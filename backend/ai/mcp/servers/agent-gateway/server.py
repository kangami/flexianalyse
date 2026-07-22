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

app = FastAPI(title="FlexiAnalyse Agent Gateway")

# connector_id -> live WebSocket ; request_id -> pending Future
_agents: dict[str, WebSocket] = {}
_pending: dict[str, asyncio.Future] = {}


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


@app.post("/rpc")
async def rpc(request: Request):
    if RPC_SECRET and request.headers.get("X-Gateway-Secret") != RPC_SECRET:
        raise HTTPException(status_code=401, detail="unauthorized")
    body = await request.json()
    connector_id = str(body.get("connector_id") or "")
    ws = _agents.get(connector_id)
    if ws is None:
        raise HTTPException(status_code=503, detail="agent offline")

    rid = uuid.uuid4().hex
    loop = asyncio.get_event_loop()
    fut: asyncio.Future = loop.create_future()
    _pending[rid] = fut
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
    finally:
        _pending.pop(rid, None)


if __name__ == "__main__":
    port = int(os.getenv("PORT") or os.getenv("HTTP_PORT", "3010"))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
