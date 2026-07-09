"""
server.py — FastAPI app exposing the agency over HTTP + SSE.

Endpoints:
    GET  /health          → config + liveness (dashboard polls this)
    POST /run             → start a crew run in the background, returns run_id
    GET  /stream/{run_id} → Server-Sent Events stream of AgentEvents

Run it:
    uvicorn fm2_agency.server:app --host 0.0.0.0 --port 8765
"""

from __future__ import annotations

import asyncio
import json
import uuid

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from .crew import build_crew
from .events import AgentEvent, bus
from .llms import describe

app = FastAPI(title="FM2 Agency — local multi-agent crew")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # tighten for anything beyond localhost
    allow_methods=["*"],
    allow_headers=["*"],
)

# Captured at startup so worker-thread callbacks can schedule onto the loop.
LOOP: asyncio.AbstractEventLoop


@app.on_event("startup")
async def _capture_loop() -> None:
    global LOOP
    LOOP = asyncio.get_running_loop()


class RunRequest(BaseModel):
    brief: str


class RunResponse(BaseModel):
    run_id: str


@app.get("/health")
async def health() -> dict:
    return {"ok": True, **describe()}


@app.post("/run", response_model=RunResponse)
async def start_run(req: RunRequest) -> RunResponse:
    if not req.brief.strip():
        raise HTTPException(400, "brief is empty")

    run_id = uuid.uuid4().hex[:12]
    bus.open(run_id)

    async def execute() -> None:
        try:
            # Kickoff event so the dashboard lights up immediately.
            await bus.emit(AgentEvent(
                run_id=run_id, agent="marina", kind="kickoff",
                msg="Brief received. Decomposing into work streams.",
                head={"author": "Marina Vidal", "arrow": "→", "target": "team"},
            ))

            crew = build_crew(run_id, LOOP)
            # CrewAI is synchronous — run it off the event loop.
            await asyncio.to_thread(crew.kickoff, inputs={"brief": req.brief})

            await bus.emit(AgentEvent(
                run_id=run_id, agent="marina", kind="final",
                msg="Delivery complete.",
                head={"author": "Marina Vidal", "arrow": "→", "target": "client"},
                final=True,
            ))
        except Exception as exc:  # surface failures to the UI instead of dying silently
            await bus.emit(AgentEvent(
                run_id=run_id, agent="marina", kind="error",
                msg=f"Run failed: {exc}",
                head={"author": "system", "arrow": "!", "target": "client"},
                final=True,
            ))
        finally:
            await bus.close(run_id)

    asyncio.create_task(execute())
    return RunResponse(run_id=run_id)


@app.get("/stream/{run_id}")
async def stream(run_id: str):
    if not bus.has(run_id):
        raise HTTPException(404, f"run {run_id} not found")

    async def gen():
        async for ev in bus.consume(run_id):
            yield {"event": ev.kind, "data": json.dumps(ev.to_dict(), ensure_ascii=False)}

    return EventSourceResponse(gen())
