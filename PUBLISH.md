# How to publish this repo

No token pasting. Use the GitHub CLI browser auth.

## One-time setup

```bash
brew install gh            # macOS (or see github.com/cli/cli#installation)
gh auth login
#   → GitHub.com → HTTPS → "Login with a web browser"
```

## Publish

```bash
cd fm2-agency

git init
git add .
git commit -m "feat: local-first CrewAI + Ollama agency with live dashboard"

gh repo create fm2-agency --public --source=. --push
```

Live at `https://github.com/<your-username>/fm2-agency`.

## Before posting on LinkedIn

1. **Actually run it once** against your 4070 Ti and capture a screen recording
   of the dashboard mid-run. That recording is the post. "Tested in production
   by me" is implicit in every file, but the video is what makes people stop
   scrolling.
2. Confirm the CrewAI version you installed matches the callback signatures in
   `src/fm2_agency/crew.py` (run `pip show crewai`). If a run errors on a
   callback, that's the place to adjust — note it honestly in the README if you
   pin a specific version.
3. Replace `<your-username>` placeholders in `README.md`.
4. The LinkedIn draft is in `docs/linkedin-post-draft.md`.

## Recommended first run

```bash
# Terminal 1 (on the GPU box)
ollama serve

# Terminal 2
./scripts/setup-models.sh
pip install -e .
uvicorn fm2_agency.server:app --host 0.0.0.0 --port 8765

# Browser
open dashboard/index.html
```
