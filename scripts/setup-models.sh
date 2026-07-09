#!/usr/bin/env bash
#
# setup-models.sh — pull the models FM2 Agency needs.
#
# Tuned for a 12 GB GPU (RTX 4070 Ti). On 12 GB you run ONE model resident at a
# time, so we pull a primary (14B, best reasoning that fits) and an optional
# faster 8B you can switch to via FM2_MODEL.
#
# On a bigger box (24 GB+), you can also enable per-role routing — see README.

set -euo pipefail

echo "==> Checking Ollama is reachable..."
if ! command -v ollama >/dev/null 2>&1; then
  echo "Ollama not found. Install from https://ollama.com first."
  exit 1
fi

# Primary: best reasoning + tool calling that fits in 12 GB.
echo "==> Pulling qwen3:14b (~8.5 GB, primary)"
ollama pull qwen3:14b

# Faster alternative for tighter VRAM or quicker runs.
echo "==> Pulling qwen3:8b (~5 GB, fast alternative)"
ollama pull qwen3:8b

cat <<'EOF'

Done.

Defaults are set for the 4070 Ti (single resident model). To use the faster 8B
as primary instead:

    export FM2_MODEL=ollama/qwen3:8b

NOTE on MoE: do NOT use qwen3:30b-a3b on a 12 GB card. It needs ~17-21 GB to
load (all experts resident) and has a known Ollama GPU-utilization issue as of
mid-2026. It's a 24 GB-card model.

EOF
