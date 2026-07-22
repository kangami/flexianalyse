"""Dial-home agent mode for the SQL MCP server.

When FLEXI_AGENT_MODE is set, instead of serving HTTP the container opens a
persistent OUTBOUND WebSocket to the FlexiAnalyse gateway and executes tool
requests against the LOCAL database. This lets a customer expose an on-premise /
private-network database to the cloud SaaS without opening any inbound port —
and the DB credentials never leave their machine (only query results transit).

Env:
  FLEXI_AGENT_MODE=1        enable agent mode (checked in server.py)
  DATABASE_URL=...          the LOCAL database (stays here)
  FLEXI_TOKEN=<jwt>         pairing token (identifies the connector to the gateway)
  FLEXI_GATEWAY_URL=wss://…/agent
"""
import asyncio
import json
import logging
import os

import websockets

from tools import SQLTools, dispatch_tool

logger = logging.getLogger("flexi-agent")

MAX_MSG = 32 * 1024 * 1024  # allow large result payloads


async def _handle_request(ws, tools, msg) -> None:
    """Run one tool request off the event loop and stream the reply back.

    dispatch_tool is SYNCHRONOUS and can block for a long time (schema reflection
    or a heavy query on a large database). Running it inline would freeze the
    asyncio loop, so the WebSocket keepalive pings stop and the gateway drops the
    connection ("Agent OFFLINE") mid-query. Offloading to a worker thread keeps the
    loop free to answer pings — long queries no longer kill the socket, and several
    requests can run at once.
    """
    rid = msg.get("id")
    try:
        result = await asyncio.to_thread(
            dispatch_tool, tools, msg.get("tool"), msg.get("params", {})
        )
    except Exception as e:
        result = {"status": "error", "message": str(e)}
    # default=str is a safety net: a column type json can't encode natively
    # (datetime, UUID, Decimal, …) would otherwise raise here — and since the send
    # failure is swallowed, the caller would just hang until it times out. Encoding
    # such values as strings guarantees a response always goes back.
    try:
        payload = json.dumps({"type": "response", "id": rid, "result": result}, default=str)
    except Exception as e:
        payload = json.dumps({"type": "response", "id": rid,
                              "result": {"status": "error", "message": f"unserializable result: {e}"}})
    try:
        await ws.send(payload)
    except Exception:
        pass  # socket closed while we were working; the gateway will retry


async def _serve(ws, tools) -> None:
    await ws.send(json.dumps({"type": "auth", "token": os.getenv("FLEXI_TOKEN", "")}))
    tasks: set = set()
    try:
        async for raw in ws:
            try:
                msg = json.loads(raw)
            except Exception:
                continue
            mtype = msg.get("type")
            if mtype == "auth_ok":
                logger.info("Agent authenticated — ready to serve queries.")
                continue
            if mtype == "auth_error":
                logger.error("Gateway rejected the token: %s", msg.get("message"))
                await ws.close()
                return
            if mtype == "request":
                t = asyncio.ensure_future(_handle_request(ws, tools, msg))
                tasks.add(t)
                t.add_done_callback(tasks.discard)
    finally:
        for t in tasks:
            t.cancel()


async def run_agent() -> None:
    db_url = os.getenv("DATABASE_URL")
    token = os.getenv("FLEXI_TOKEN")
    gateway = os.getenv("FLEXI_GATEWAY_URL", "wss://flexianalyse-gateway.onrender.com/agent")
    if not db_url or not token:
        raise SystemExit("Agent mode requires DATABASE_URL and FLEXI_TOKEN")

    # Connect to the LOCAL database once (fails fast with a clear error).
    tools = SQLTools(db_url)
    logger.info("Local database reachable (%s). Dialing home to %s", tools.dialect, gateway)

    backoff = 1
    while True:
        try:
            async with websockets.connect(
                gateway, ping_interval=20, ping_timeout=20, max_size=MAX_MSG,
            ) as ws:
                backoff = 1
                await _serve(ws, tools)
        except Exception as e:
            logger.warning("Gateway connection lost (%s) — reconnecting in %ss", e, backoff)
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 30)
