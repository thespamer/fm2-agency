# FM2 Agency

A local-first multi-agent crew that turns a one-line brief into a stack of
deliverables — with a live operations dashboard so you can watch the agents
work, not just read a terminal log.

Built on **CrewAI** + **Ollama**. No external API. No tokens leaving your
network. Runs on a single consumer GPU.

```
   brief ──▶ ┌─────────┐ delegates ┌──────────┐ ┌──────────┐ ┌────────┐ ┌──────────┐
             │ Marina  │──────────▶│  Rafael  │▶│  Camila  │▶│ Bruno  │▶│  Helena  │
             │  (Ops)  │           │(research)│ │(strategy)│ │(script)│ │ (review) │
             └────┬────┘           └────┬─────┘ └────┬─────┘ └───┬────┘ └────┬─────┘
                  │                     │            │           │           │
                  ▼                     ▼            ▼           ▼           ▼
            ┌──────────────────────────────────────────────────────────────────┐
            │  SSE stream ──▶ live dashboard (status, reasoning, deliverables)  │
            └──────────────────────────────────────────────────────────────────┘
```

Most CrewAI tutorials show you `verbose=True` scrolling past in a terminal.
FM2 gives you an actual operations floor: each agent has a status, its
reasoning streams in, and deliverables assemble on the right as markdown you
can download — per artifact or as one bundle.

---

## Why local, why this hardware

This was built and tuned on an **RTX 4070 Ti (12 GB VRAM)** running Ollama. That
constraint shaped every model decision, so let's be precise about it instead of
hand-waving "just use a local model."

**The 12 GB rule that everyone gets wrong:** you cannot run several different
models resident at once on 12 GB. A dense 14B at Q4_K_M is ~8.5 GB; an 8B at Q4
is ~5 GB. Try to hold both and Ollama spills layers to system RAM and throughput
collapses. So FM2 keeps **one model hot for the whole run** and varies behavior
by prompt and temperature, not by swapping models per agent. On a 12 GB card,
swapping models per role is *slower*, not smarter — load/unload costs seconds
each time and dominates a short run.

**Model choice — Qwen3 14B (Q4_K_M, ~8.5 GB):** best reasoning that fits in
12 GB, and — the part that matters for agents — the most reliable tool calling
of the open local families as of mid-2026 (it rarely drops parameters or
hallucinates calls). For faster runs, `qwen3:8b` (~5 GB) is a drop-in via an env
var.

**Why not the shiny MoE:** Qwen3-30B-A3B looks perfect on paper (3B active, 30B
total quality). But MoE models must load *all* experts into memory — ~17–21 GB
at Q4 — so it does **not** fit on 12 GB, and as of mid-2026 it has a known
GPU-utilization issue in Ollama (#10458). It's a 24 GB-card model. FM2's config
is ready for it: point `OLLAMA_HOST` at a bigger box and flip
`FM2_ROLE_ROUTING=1`.

**Remote Ollama:** the GPU doesn't have to be the machine running the server.
Point `OLLAMA_HOST` at another box on your LAN or Tailnet
(`export OLLAMA_HOST=http://100.x.y.z:11434`) and the crew runs there while the
dashboard runs wherever you like.

| Your GPU | Recommended setup |
|----------|-------------------|
| 12 GB (4070 Ti, 4070, 3060, 5070) | `qwen3:14b`, single resident model (default) |
| 16 GB (4060 Ti 16GB, 4070 Ti Super) | `qwen3:14b` at Q5, or enable role routing with 8B |
| 24 GB (3090, 4090) | enable `FM2_ROLE_ROUTING=1`; `qwen3:30b-a3b` MoE becomes viable |
| Apple Silicon (32 GB+) | works via Ollama Metal; `qwen3:14b` or `30b-a3b` |

---

## Quickstart

### 1. Pull the models

```bash
# On the box with the GPU
ollama serve &                 # if not already running
./scripts/setup-models.sh      # pulls qwen3:14b + qwen3:8b
```

### 2. Install and run the backend

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e .               # or: pip install -r requirements.txt

# If Ollama is on another machine:
# export OLLAMA_HOST=http://192.168.x.x:11434

uvicorn fm2_agency.server:app --host 0.0.0.0 --port 8765
```

Check it's alive:

```bash
curl http://localhost:8765/health
# {"ok":true,"ollama_host":"http://localhost:11434","primary_model":"ollama/qwen3:14b",...}
```

### 3. Open the dashboard

Open `dashboard/index.html` in a browser. Confirm the backend URL in the top
bar (defaults to `http://localhost:8765`), write a brief, click **start crew**.

The bar shows `backend ok` with your model + host when connected. Expect a full
run to take **several minutes** — local 14B inference is not instant, and the
dashboard reflects real work, not a canned animation.

### Or skip the dashboard entirely

```bash
python -m fm2_agency.run_cli "Go-to-market plan for a B2B SaaS in Brazil"
# deliverables saved to ./out/<timestamp>/*.md
```

---

## How it works

**`llms.py`** — model routing. One resident model on 12 GB; per-role routing
when you have the VRAM. This is the file to read if you want to understand the
hardware reasoning.

**`events.py`** — a per-run event bus. Each run gets an `asyncio.Queue`; CrewAI
callbacks (which run in a worker thread) push events onto it; the SSE endpoint
drains it to the browser. Swap for Redis pub/sub if you go multi-tenant.

**`crew.py`** — the five agents and four tasks. `Process.hierarchical` with
Marina as the explicit `manager_agent`. Each agent's `step_callback` streams its
reasoning; each task's `callback` streams the finished deliverable as markdown.

**`server.py`** — FastAPI. `POST /run` kicks off a crew in the background and
returns a `run_id`; `GET /stream/{run_id}` is the SSE feed; `GET /health` lets
the dashboard show live config.

**`dashboard/index.html`** — single file, no build step. Consumes the SSE feed,
maps whatever role/name CrewAI emits onto the five personas, renders reasoning
in monospace and deliverables as rendered markdown, and lets you download each
artifact or a bundled `.md`.

---

## Honest notes

- **CrewAI changes its API.** This targets CrewAI ≥ 0.80, where `manager_agent`
  is preferred over `manager_llm` for hierarchical crews and callbacks pass
  `TaskOutput`/step objects. If you're on a different version, the callback
  signatures in `crew.py` are the first thing to check. Run `pip show crewai`.
- **Local models are slower and rougher** than frontier cloud models. The
  reasoning streams are raw ReAct traces, not polished prose. That's the trade
  you make for zero API cost and data that never leaves your perimeter.
- **Tools are not wired by default.** The agents reason and write; they don't
  browse. To give Rafael real web search, plug in a self-hosted SearxNG or a
  search tool and add it to his `tools=[...]`. Kept out of the box so the repo
  runs with zero external dependencies.

## Roadmap

- [ ] Real research tools (self-hosted SearxNG) for the researcher agent
- [ ] CrewAI `memory=True` with local ChromaDB for cross-run continuity
- [ ] Langfuse (self-hosted) tracing for per-agent latency/quality
- [ ] Dockerfile + Helm chart for homelab Kubernetes deploy
- [ ] Cancel endpoint (currently the dashboard just detaches)

## License

MIT. Fork it, change the crew, point it at your own briefs.

## Author

Juliano Souza — Fractional CTO, São Paulo / Lisbon. Built on a homelab
4070 Ti because the most interesting AI work right now is the kind that
doesn't phone home.
