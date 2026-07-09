"""
events.py — per-run event bus that feeds the live dashboard over SSE.

Each run gets its own asyncio.Queue. CrewAI callbacks (which run in a worker
thread) push events onto the queue via the main loop; the SSE endpoint drains
the queue and streams events to the browser.

For a single homelab box this in-memory bus is plenty. If you ever go
multi-tenant, swap the dict-of-queues for Redis pub/sub — the AgentEvent shape
stays the same.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import AsyncIterator, Literal, Optional


EventKind = Literal["kickoff", "delegate", "think", "tool", "deliver", "review", "final", "error"]


@dataclass
class AgentEvent:
    run_id: str
    agent: str                      # marina | rafael | camila | bruno | helena
    kind: EventKind
    msg: str
    head: dict = field(default_factory=dict)        # {author, arrow, target}
    thought: Optional[str] = None
    output: Optional[dict] = None                    # {title, by, markdown}
    final: bool = False
    t: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "agent": self.agent,
            "kind": self.kind,
            "msg": self.msg,
            "head": self.head,
            "thought": self.thought,
            "output": self.output,
            "final": self.final,
            "t": self.t,
        }


class EventBus:
    """Routes events to per-run queues consumed by the SSE endpoint."""

    def __init__(self) -> None:
        self._queues: dict[str, asyncio.Queue] = {}

    def open(self, run_id: str) -> None:
        self._queues[run_id] = asyncio.Queue(maxsize=1024)

    def has(self, run_id: str) -> bool:
        return run_id in self._queues

    async def emit(self, event: AgentEvent) -> None:
        q = self._queues.get(event.run_id)
        if q is not None:
            await q.put(event)

    def emit_threadsafe(self, event: AgentEvent, loop: asyncio.AbstractEventLoop) -> None:
        """Call this from inside a CrewAI callback (worker thread)."""
        q = self._queues.get(event.run_id)
        if q is not None:
            # put_nowait avoids needing to await from the worker thread; if the
            # queue is full we drop the event rather than block the crew.
            try:
                loop.call_soon_threadsafe(q.put_nowait, event)
            except asyncio.QueueFull:
                pass

    async def close(self, run_id: str) -> None:
        q = self._queues.get(run_id)
        if q is not None:
            await q.put(None)  # sentinel → ends the SSE stream

    async def consume(self, run_id: str) -> AsyncIterator[AgentEvent]:
        q = self._queues.get(run_id)
        if q is None:
            raise KeyError(run_id)
        try:
            while True:
                ev = await q.get()
                if ev is None:
                    break
                yield ev
        finally:
            # Clean up once the consumer disconnects or the run ends.
            self._queues.pop(run_id, None)


bus = EventBus()
