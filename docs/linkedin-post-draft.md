# LinkedIn post draft — fm2-agency

> Post this AFTER you've run it and captured a screen recording of the dashboard
> mid-run. The video is what makes the post. Swap the repo link at the end.

---

Every CrewAI tutorial shows you the same thing: `verbose=True` and a wall of
text scrolling past in a terminal.

I wanted to actually *see* my agents work. So I built an operations floor.

FM2 Agency is a 5-agent crew — ops lead, researcher, strategist, writer,
reviewer — that turns a one-line brief into a stack of deliverables. It runs
100% local on my homelab RTX 4070 Ti via Ollama. No external API. No tokens
leaving my network. ~R$ 0.80 of electricity per run.

The part I'm proud of isn't the agents — it's being honest about the hardware.

Most "just run it locally" content skips the constraint that actually matters:
**on a 12 GB GPU you cannot hold several models resident at once.** A 14B at Q4
is ~8.5 GB. An 8B is ~5 GB. Try to run both and Ollama spills to system RAM and
your throughput dies. So FM2 keeps ONE model hot for the whole run and varies
behavior by prompt and temperature — which is also *faster*, because model
swapping on 12 GB costs seconds you don't get back.

A few specifics I had to get right:

→ Qwen3 14B as the primary — best reasoning that fits in 12 GB, and the most
reliable tool-calling of the open local families right now.

→ I deliberately did NOT use the trendy MoE (Qwen3-30B-A3B). It needs ~17-21 GB
to load all experts, so it doesn't fit on 12 GB, and it has a known Ollama
GPU-utilization issue as of mid-2026. It's a 24 GB-card model. The config is
ready for it the day I upgrade.

→ Live reasoning streams over SSE; deliverables assemble as downloadable
markdown. CrewAI callbacks run in a worker thread, so the event bus marshals
them onto the asyncio loop. Small detail, easy to get wrong, breaks silently.

The whole thing is open source. Fork it, change the crew, point it at your own
briefs.

[VIDEO: dashboard mid-run]

Repo: github.com/<your-handle>/fm2-agency
MIT.

---

#localai #crewai #ollama #selfhosted #aiagents #cto

---

## Short variant (X / Twitter)

Built an operations floor for local AI agents.

5-agent CrewAI crew, 100% local on a 4070 Ti via Ollama. Watch them work —
reasoning streams live, deliverables assemble as downloadable markdown.

The honest part: on 12 GB you can't hold multiple models resident. One hot
model beats per-role swapping. Qwen3 14B, not the MoE (doesn't fit).

Repo: [link] · MIT

---

## Notes for Juliano

- This post and the claude-code-arsenal post are a PAIR. Space them ~1 week
  apart. Arsenal first (lower effort, proves Anthropic-ecosystem fluency), this
  second (the viral one — visual + local + opinionated).
- The hook here is the contrast: "everyone shows terminal verbose, I built an
  ops floor." Lead with the video.
- The 12 GB reasoning is your moat. Anyone can `pip install crewai`. Almost
  nobody explains *why* the model choices are what they are. That paragraph is
  what signals senior operator vs tutorial-follower.
- Cross-post to r/LocalLLaMA with a different framing: less "look what I built,"
  more "here's the 12 GB model-routing reasoning + a dashboard, code inside."
  That community rewards rigor and punishes self-promotion — lead with the
  technical insight, mention the repo at the end.
- Tag CrewAI and Ollama if they're active on LinkedIn — both reshare community
  builds.
- When comments come in, engage. Each is a potential Fractional CTO conversation.
