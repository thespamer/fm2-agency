"""
run_cli.py — run the agency from the terminal, no server/dashboard needed.

Usage:
    python -m fm2_agency.run_cli "Your brief here"
    # or, if no arg, it uses a default brief.

This is the fastest way to confirm your Ollama + model setup works before you
wire up the dashboard. Output (the deliverables) is printed and also saved to
./out/<timestamp>/ as markdown files.
"""

from __future__ import annotations

import asyncio
import sys
from datetime import datetime
from pathlib import Path

import os
os.environ.setdefault("CREWAI_TRACING_ENABLED", "false")
os.environ.setdefault("OTEL_SDK_DISABLED", "true")

from .crew import build_crew, ROSTER_BY_ID
from .llms import describe


DEFAULT_BRIEF = (
    "Content strategy for a YouTube channel about local AI for CTOs — "
    "first 5 videos, editorial angle, and a full script for the pilot episode."
)


def main() -> None:
    brief = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_BRIEF

    cfg = describe()
    print("FM2 Agency — local run")
    print(f"  Ollama:  {cfg['ollama_host']}")
    print(f"  Model:   {cfg['primary_model']}")
    print(f"  Routing: {'per-role' if cfg['role_routing'] else 'single model (12 GB safe)'}")
    print(f"  Brief:   {brief}\n")
    print("Running... (local models are slow; expect several minutes)\n")

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # The CLI doesn't stream to a dashboard, so build_crew still wants a loop for
    # its callbacks; events just won't be consumed, which is fine.
    crew = build_crew(run_id="cli", loop=loop)
    result = crew.kickoff(inputs={"brief": brief})

    # Persist whatever the tasks produced.
    out_dir = Path("out") / datetime.now().strftime("%Y%m%d-%H%M%S")
    out_dir.mkdir(parents=True, exist_ok=True)

    # CrewAI's result object exposes task outputs; save each.
    tasks_output = getattr(result, "tasks_output", None) or []
    for i, t in enumerate(tasks_output, 1):
        raw = getattr(t, "raw", None) or str(t)
        (out_dir / f"{i:02d}-output.md").write_text(str(raw), encoding="utf-8")

    print(f"\nDone. Deliverables saved to {out_dir}/")
    print("\nFinal result:\n")
    print(str(result)[:2000])


if __name__ == "__main__":
    main()
