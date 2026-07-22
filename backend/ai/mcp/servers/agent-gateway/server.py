"""FlexiAnalyse Agent Gateway.

Holds the persistent WebSocket connections from customers' dial-home agents
(on-prem / private-network databases) and exposes an internal HTTP RPC the cloud
API calls to run a tool against a specific connector's agent.

Flow:
  agent  --WSS-->  /agent   (auth with a signed token → bound to a connector_id)
  API    --HTTP--> /rpc      ({connector_id, tool_name, params}) → forwarded over
                             the agent's socket, response awaited and returned.

Single process on purpose: it must hold the live sockets in memory. WebSockets are
cheap when idle, so one process serves many agents; scale later with Redis pub/sub
to route across instances.

Env:
  AGENT_TOKEN_SECRET    HS256 secret to verify agent pairing tokens (shared w/ API)
  AGENT_GATEWAY_SECRET  shared secret the API must present on /rpc
  AGENT_RPC_TIMEOUT     seconds to wait for an agent response (default 60)
  PORT / HTTP_PORT      listen port
"""
import os
import json
import uuid
import asyncio
import logging

import jwt
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, HTTPException

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("agent-gateway")

TOKEN_SECRET = os.getenv("AGENT_TOKEN_SECRET", "")
RPC_SECRET = os.getenv("AGENT_GATEWAY_SECRET", "")
RPC_TIMEOUT = float(os.getenv("AGENT_RPC_TIMEOUT", "120"))
# How long /rpc waits for a briefly-offline agent to (re)connect before giving up.
# Agents reconnect within ~2s after a drop, so a short grace bridges the gap and
# keeps a query from failing just because the socket was cycling.
WAIT_ONLINE = float(os.getenv("AGENT_WAIT_ONLINE", "10"))

app = FastAPI(title="FlexiAnalyse Agent Gateway")

# connector_id -> live WebSocket ; request_id -> pending Future
_agents: dict[str, WebSocket] = {}
_pending: dict[str, asyncio.Future] = {}
# connector_id -> set of in-flight request ids, so a disconnect can fail them fast.
_inflight: dict[str, set] = {}


async def _wait_online(connector_id: str) -> WebSocket | None:
    """Return the agent socket, waiting up to WAIT_ONLINE for a reconnect."""
    ws = _agents.get(connector_id)
    if ws is not None:
        return ws
    loop = asyncio.get_event_loop()
    deadline = loop.time() + WAIT_ONLINE
    while loop.time() < deadline:
        await asyncio.sleep(0.25)
        ws = _agents.get(connector_id)
        if ws is not None:
            return ws
    return None


@app.get("/health")
async def health():
    return {"status": "healthy", "agents": len(_agents)}


@app.get("/status/{connector_id}")
async def status(connector_id: str):
    return {"online": connector_id in _agents}


@app.websocket("/agent")
async def agent_ws(ws: WebSocket):
    await ws.accept()
    connector_id: str | None = None
    try:
        # First message must authenticate with a signed token.
        first = json.loads(await ws.receive_text())
        if first.get("type") != "auth":
            await ws.send_text(json.dumps({"type": "auth_error", "message": "auth expected"}))
            await ws.close(code=4001)
            return
        try:
            payload = jwt.decode(first.get("token", ""), TOKEN_SECRET, algorithms=["HS256"])
        except Exception as e:
            await ws.send_text(json.dumps({"type": "auth_error", "message": "invalid token"}))
            await ws.close(code=4003)
            logger.warning("Rejected agent (bad token): %s", e)
            return
        connector_id = str(payload.get("connector_id") or "")
        if not connector_id:
            await ws.close(code=4003)
            return

        _agents[connector_id] = ws
        _inflight.setdefault(connector_id, set())
        await ws.send_text(json.dumps({"type": "auth_ok"}))
        logger.info("Agent ONLINE — connector %s (total %d)", connector_id, len(_agents))

        # Pump responses back to the awaiting /rpc callers.
        while True:
            msg = json.loads(await ws.receive_text())
            if msg.get("type") == "response":
                fut = _pending.get(msg.get("id"))
                if fut and not fut.done():
                    fut.set_result(msg.get("result"))
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.warning("Agent WS error (connector %s): %s", connector_id, e)
    finally:
        if connector_id and _agents.get(connector_id) is ws:
            del _agents[connector_id]
            logger.info("Agent OFFLINE — connector %s", connector_id)
            # Fail this agent's in-flight requests immediately instead of letting
            # their callers hang until RPC_TIMEOUT — the socket that would carry
            # the reply is gone.
            for rid in list(_inflight.get(connector_id, ())):
                fut = _pending.get(rid)
                if fut and not fut.done():
                    fut.set_exception(ConnectionError("agent disconnected mid-request"))
            _inflight.pop(connector_id, None)


@app.post("/rpc")
async def rpc(request: Request):
    if RPC_SECRET and request.headers.get("X-Gateway-Secret") != RPC_SECRET:
        raise HTTPException(status_code=401, detail="unauthorized")
    body = await request.json()
    connector_id = str(body.get("connector_id") or "")
    # Tolerate a socket that's briefly cycling: wait a short grace for a reconnect.
    ws = await _wait_online(connector_id)
    if ws is None:
        raise HTTPException(status_code=503, detail="agent offline")

    rid = uuid.uuid4().hex
    loop = asyncio.get_event_loop()
    fut: asyncio.Future = loop.create_future()
    _pending[rid] = fut
    _inflight.setdefault(connector_id, set()).add(rid)
    try:
        await ws.send_text(json.dumps({
            "type": "request",
            "id": rid,
            "tool": body.get("tool_name"),
            "params": body.get("params", {}),
        }))
        return await asyncio.wait_for(fut, timeout=RPC_TIMEOUT)
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="agent timed out")
    except ConnectionError:
        # Socket dropped mid-request (agent disconnected) — surface it as offline
        # so the caller can retry rather than treating it as a hard failure.
        raise HTTPException(status_code=503, detail="agent disconnected mid-request")
    finally:
        _pending.pop(rid, None)
        inflight = _inflight.get(connector_id)
        if inflight is not None:
            inflight.discard(rid)


if __name__ == "__main__":
    port = int(os.getenv("PORT") or os.getenv("HTTP_PORT", "3010"))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
