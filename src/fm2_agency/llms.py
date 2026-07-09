"""
llms.py — model routing for the FM2 agency.

Hardware reality (read this before changing models):

    The RTX 4070 Ti has 12 GB of VRAM. That is the single most important
    constraint in this whole project. It dictates which models you can run and,
    crucially, how many you can run AT ONCE.

    A dense 14B model at Q4_K_M is ~8.5 GB. An 8B at Q4 is ~5 GB. You CANNOT
    hold a 14B and an 8B resident simultaneously on 12 GB — together they need
    ~13.5 GB plus KV cache, and Ollama will spill layers to system RAM and the
    throughput collapses.

    So this agency does NOT assign a different always-resident model per agent.
    Instead it uses ONE primary model for every agent, and lets Ollama keep that
    single model hot across the whole run. This is faster end-to-end than
    swapping models per role, because model load/unload on a 12 GB card costs
    several seconds each time and dominates a short run.

    If you point OLLAMA_HOST at a bigger box (a 24 GB 3090/4090, or a remote
    server), set ROLE_ROUTING=1 to enable per-role models again — the routing
    table below is ready for it.

MoE note:
    Qwen3-30B-A3B (MoE) looks tempting — 3B active params, 30B total quality.
    But at Q4 it needs ~17-21 GB to LOAD (all experts must be resident), so it
    does NOT fit on 12 GB, and as of mid-2026 it has a known GPU-utilization
    issue in Ollama (#10458). Skip it on the 4070 Ti. It shines on 24 GB cards.

Recommended models for the 4070 Ti (verified mid-2026):
    - qwen3:14b        ~8.5 GB Q4_K_M   best reasoning + tool calling that fits
    - qwen3:8b         ~5 GB   Q4_K_M   faster, great for executive/IO-bound roles
    - qwen2.5-coder:7b ~5 GB            if a role is code-heavy

Qwen3 is chosen deliberately: as of 2026 it has the most stable tool calling of
the open local families (rarely drops parameters or hallucinates calls), which
matters a lot for CrewAI agents that use tools.
"""

from __future__ import annotations

import os

from crewai import LLM

# ---------------------------------------------------------------------------
# Connection
# ---------------------------------------------------------------------------
# Point this at your Ollama. Local default below; for a remote box on your
# Tailscale net or LAN, export OLLAMA_HOST=http://100.x.y.z:11434
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
os.environ.setdefault("OPENAI_API_KEY", "ollama-local")

# Primary model — the one kept hot for the whole run. Override with FM2_MODEL.
PRIMARY_MODEL = os.getenv("FM2_MODEL", "ollama/qwen3:14b")

# Faster secondary, used only when ROLE_ROUTING is enabled and the box has VRAM.
FAST_MODEL = os.getenv("FM2_FAST_MODEL", "ollama/qwen3:8b")

# Set ROLE_ROUTING=1 only if your Ollama host has >16 GB VRAM. On a 12 GB
# 4070 Ti, leave this off (0) so a single model stays resident.
ROLE_ROUTING = os.getenv("FM2_ROLE_ROUTING", "0") == "1"


def _llm(model: str, temperature: float) -> LLM:
    """Build a CrewAI LLM bound to the configured Ollama host."""
    base = OLLAMA_HOST
    if not base.startswith(("http://", "https://")):
        base = "http://" + base
    return LLM(
        model=model,
        base_url=base,
        temperature=temperature,
        api_key="ollama-local",
    )


def for_role(role: str) -> LLM:
    """
    Return the LLM an agent should use.

    On a 12 GB card (ROLE_ROUTING off) every role gets PRIMARY_MODEL so Ollama
    keeps exactly one model hot. On a bigger box (ROLE_ROUTING on) reasoning
    roles get the primary and IO-bound roles get the faster model.
    """
    if not ROLE_ROUTING:
        # Temperature still varies by role even on a single model.
        temp = {
            "manager": 0.2,
            "researcher": 0.4,
            "strategist": 0.3,
            "writer": 0.6,
            "reviewer": 0.3,
        }.get(role, 0.3)
        return _llm(PRIMARY_MODEL, temp)

    # Multi-model routing (only when you have the VRAM for it).
    routing = {
        "manager":    (PRIMARY_MODEL, 0.2),
        "researcher": (FAST_MODEL,    0.4),
        "strategist": (PRIMARY_MODEL, 0.3),
        "writer":     (FAST_MODEL,    0.6),
        "reviewer":   (FAST_MODEL,    0.3),
    }
    model, temp = routing.get(role, (PRIMARY_MODEL, 0.3))
    return _llm(model, temp)


def describe() -> dict:
    """Used by the /health endpoint so the dashboard can show the config."""
    return {
        "ollama_host": OLLAMA_HOST,
        "primary_model": PRIMARY_MODEL,
        "fast_model": FAST_MODEL if ROLE_ROUTING else None,
        "role_routing": ROLE_ROUTING,
    }
