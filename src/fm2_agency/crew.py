"""
crew.py — the FM2 agency: five agents that turn a brief into deliverables.

The cast mirrors a real content/strategy shop:
    marina   — Head of Operations (manager, delegates and synthesizes)
    rafael   — Researcher (market signals, personas)
    camila   — Strategist (positioning, editorial angle)
    bruno    — Writer (scripts, hooks, copy)
    helena   — Editorial Reviewer (QA, fact/claim validation)

Process is hierarchical: Marina coordinates. On a 12 GB box every agent shares
one resident model (see llms.py), so "hierarchical" here is about delegation
logic, not about running five models at once.
"""

from __future__ import annotations

import asyncio

from crewai import Agent, Crew, Process, Task

from .events import AgentEvent, bus
from .llms import for_role


# Map a CrewAI role string to our short agent id + display name.
ROSTER = {
    "Head of Operations":  ("marina", "Marina Vidal"),
    "Researcher":          ("rafael", "Rafael Costa"),
    "Content Strategist":  ("camila", "Camila Reis"),
    "Scriptwriter":        ("bruno",  "Bruno Almeida"),
    "Editorial Reviewer":  ("helena", "Helena Pires"),
}


def _resolve(role_or_name: str) -> str:
    """Best-effort mapping from a CrewAI role/name to our agent id."""
    if not role_or_name:
        return "marina"
    key = role_or_name.strip()
    if key in ROSTER:
        return ROSTER[key][0]
    low = key.lower()
    for role, (aid, name) in ROSTER.items():
        if aid in low or name.lower() in low or role.lower() in low:
            return aid
    return "marina"


def build_crew(run_id: str, loop: asyncio.AbstractEventLoop) -> Crew:
    """Construct the crew, wiring callbacks that stream events to the dashboard."""

    # ----- callback factories ------------------------------------------------
    def step_cb_for(agent_id: str):
        """Emits a 'think' event for each intermediate reasoning step."""
        def cb(step_output) -> None:
            thought = getattr(step_output, "log", None) or str(step_output)
            ev = AgentEvent(
                run_id=run_id,
                agent=agent_id,
                kind="think",
                msg="(reasoning)",
                head={"author": ROSTER_BY_ID[agent_id], "arrow": "·", "target": "working"},
                thought=thought[:800],
            )
            bus.emit_threadsafe(ev, loop)
        return cb

    def task_cb_for(agent_id: str, label: str):
        """Emits a 'deliver' event with the finished artifact as markdown."""
        def cb(task_output) -> None:
            raw = getattr(task_output, "raw", None) or str(task_output)
            ev = AgentEvent(
                run_id=run_id,
                agent=agent_id,
                kind="deliver",
                msg=f"{label} delivered.",
                head={"author": ROSTER_BY_ID[agent_id], "arrow": "→", "target": "Marina"},
                output={"title": label, "by": agent_id, "markdown": str(raw)[:8000]},
            )
            bus.emit_threadsafe(ev, loop)
        return cb

    # ----- agents ------------------------------------------------------------
    marina = Agent(
        role="Head of Operations",
        goal="Decompose the client brief into work streams, delegate to specialists, "
             "and guarantee the final delivery honors the brief.",
        backstory="Twelve years running operations at a São Paulo content agency before "
                  "moving into AI orchestration. Direct, deadline-obsessed.",
        llm=for_role("manager"),
        allow_delegation=True,
        verbose=True,
        step_callback=step_cb_for("marina"),
    )

    rafael = Agent(
        role="Researcher",
        goal="Surface market signals, demand gaps, and audience personas relevant to the brief.",
        backstory="Ex-strategy-consulting analyst with reflexes for spotting signal before "
                  "the market prices it in.",
        llm=for_role("researcher"),
        verbose=True,
        step_callback=step_cb_for("rafael"),
    )

    camila = Agent(
        role="Content Strategist",
        goal="Define editorial angle, positioning, and primary audience. Differentiation is non-negotiable.",
        backstory="Brand-positioning background at Series-B startups. Allergic to generic content.",
        llm=for_role("strategist"),
        verbose=True,
        step_callback=step_cb_for("camila"),
    )

    bruno = Agent(
        role="Scriptwriter",
        goal="Turn strategy into scripts/copy with a strong hook and clear structure.",
        backstory="Freelance scriptwriter for Brazilian tech channels with 500k+ subscribers. "
                  "Believes a weak hook kills a good video.",
        llm=for_role("writer"),
        verbose=True,
        step_callback=step_cb_for("bruno"),
    )

    helena = Agent(
        role="Editorial Reviewer",
        goal="Review drafts for technical consistency, fluency, and claims that age badly.",
        backstory="Former tech-magazine editor with a clinical eye for shaky arguments and "
                  "dates that won't hold up.",
        llm=for_role("reviewer"),
        verbose=True,
        step_callback=step_cb_for("helena"),
    )

    # ----- tasks -------------------------------------------------------------
    research = Task(
        description=(
            "Research market signals for this brief: {brief}\n"
            "Return: (1) 5 themes with traction and a competition rating (low/medium/high), "
            "and (2) 3 primary audience personas. Be concrete and specific."
        ),
        expected_output="A demand map of 5 themes + 3 personas, in markdown.",
        agent=rafael,
        callback=task_cb_for("rafael", "Demand map & personas"),
    )

    strategy = Task(
        description=(
            "Using the research, define the editorial angle and primary audience profile. "
            "Differentiation is mandatory — reject generic positioning. Include a one-line "
            "promise and a short content calendar."
        ),
        expected_output="A positioning doc + content calendar, in markdown.",
        agent=camila,
        context=[research],
        callback=task_cb_for("camila", "Positioning & calendar"),
    )

    script = Task(
        description=(
            "Write the pilot piece following the strategy. Provide 3 hook options with "
            "pros/cons, then a full script with timestamps. Tone: operator, first person."
        ),
        expected_output="3 hooks + a full pilot script, in markdown.",
        agent=bruno,
        context=[strategy],
        callback=task_cb_for("bruno", "Pilot script (draft)"),
    )

    review = Task(
        description=(
            "Review the script. Assess hook, transitions, references that may age badly, and "
            "technical clarity. Return review notes with a status (approved / needs-fix) and, "
            "if needed, the corrected final version."
        ),
        expected_output="Review notes + approved final script, in markdown.",
        agent=helena,
        context=[script],
        callback=task_cb_for("helena", "Review notes & final"),
    )

    crew = Crew(
        agents=[rafael, camila, bruno, helena],
        tasks=[research, strategy, script, review],
        process=Process.hierarchical,
        manager_agent=marina,         # explicit manager (newer CrewAI prefers this over manager_llm)
        manager_llm=for_role("manager"),
        verbose=True,
    )
    return crew


# Reverse lookup id → display name, built once.
ROSTER_BY_ID = {aid: name for (_role, (aid, name)) in ROSTER.items()}
