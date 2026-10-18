# Ultron Web · 奥创计划

A lightweight public web chat powered by the OpenAI Responses API. FastAPI backend, vanilla HTML/CSS/JS frontend, Render deployment.

## Implemented
- Responsive single-page chat with Enter to send, Shift+Enter for newline, loading state, duplicate-submit prevention, clear chat and safe text rendering.
- Multi-turn context sent from browser tab; refreshing loses the conversation. **No database, cross-device sync, authentication, or long-term memory.**
- OpenAI Responses API server-side, system instructions, configurable model/token budget, input/history/body limits, basic per-IP in-memory rate limiting and sanitized upstream errors.
- `/health` health check and mocked pytest suite.

**Rendering note:** Newlines are preserved, but Markdown syntax is displayed as plain text rather than rich formatted HTML. This avoids untrusted HTML injection. Rich Markdown is a future enhancement.

## Stack and layout
- Python 3.10+, FastAPI, Uvicorn, official `openai` Python SDK, pytest, httpx.
- `main.py`: routes, config, rate limiter, Responses API integration.
- `static/index.html`, `style.css`, `app.js`: browser UI.
- `tests/`: isolated mock tests.
- `render.yaml`: Render Blueprint; `.env.example`: configuration template.
- `AGENT_GUIDE.md`: handoff and roadmap; `ULTRON_AGENT_HANDOFF.md`: original task specification.

## Local setup (macOS)
```bash
cd ultron-web
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
```
Edit `.env` and replace the placeholder with your actual key. **Do not commit `.env`.** The app does not automatically load `.env`; export it in your shell before starting:
```bash
set -a
source .env
set +a
uvicorn main:app --host 127.0.0.1 --port 8000
```
Open http://127.0.0.1:8000/ and check http://127.0.0.1:8000/health.

## Configuration
| Variable | Default | Description |
|---|---|---|
| `OPENAI_API_KEY` | required | Secret server-side API key |
| `OPENAI_MODEL` | `gpt-4.1-mini` | Model available to your API account |
| `MAX_OUTPUT_TOKENS` | `1200` | Output token cap, clamped to 64–4096 |
| `RATE_LIMIT_PER_MINUTE` | `10` | Per-process, per-peer IP requests/minute |
| `MAX_MESSAGE_CHARS` | `4000` | Per message, clamped to 1–20000 |
| `MAX_HISTORY_MESSAGES` | `20` | Max request messages, clamped to 1–50 |
| `MAX_REQUEST_BYTES` | `100000` | Body bytes, clamped to 1000–250000 |
| `PORT` | platform | Uvicorn listening port |

If changing `MAX_MESSAGE_CHARS`, also adjust the frontend textarea `maxlength` in `static/index.html`. Model configuration and output token limit are centralized in `main.py`.

## API
- `GET /`: UI.
- `GET /health`: `{ "status": "ok" }`.
- `POST /api/chat`: `{"messages":[{"role":"user","content":"Hello"}]}` → `{"reply":"..."}`. Each message role is `user` or `assistant`, final message must be `user`.
- Errors use `{ "detail": "..." }` with HTTP 4xx/5xx; malformed inputs return 422.

## Tests
```bash
python -m pytest -q
```
Mock tests do not make real paid OpenAI calls. For a real end-to-end check, supply a valid key and send a chat in the UI; this consumes API credits.

## GitHub upload
Create a new **empty** repository on github.com, then from the project root:
```bash
git init
git add .
git commit -m "Initial Ultron Web"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
git push -u origin main
```
Confirm `.env` is absent from `git status` and commits. If a key was ever committed, rotate/revoke it; removing the file is insufficient.

## Render deployment
1. Sign in to Render and connect GitHub. Choose **New → Blueprint** and select the uploaded repository (uses `render.yaml`), or create a Python Web Service manually.
2. Manual build command: `pip install -r requirements.txt`. Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`. Health check: `/health`.
3. In Render service **Environment**, set `OPENAI_API_KEY` as a secret and optionally `OPENAI_MODEL` to a model your API account can access. Never paste the key into GitHub or YAML.
4. Start deployment and inspect Render **Events/Logs** for build or runtime errors. Open `https://YOUR-SERVICE.onrender.com/health`, then visit the homepage and send a short test message.
5. For updates, commit and push to `main`, then watch Render automatic deployment (or manually deploy from the dashboard).

Render free-plan eligibility, sleeping behavior and limits may change; consult Render's current terms.

## Troubleshooting
- **Startup / missing dependency:** inspect Render build logs, verify `requirements.txt`, Python runtime and start command.
- **503 service not configured:** set `OPENAI_API_KEY` in Render and redeploy.
- **503 configuration error:** invalid/revoked API key; check secret and account.
- **502 upstream error:** verify model availability, account credits and OpenAI API status; inspect sanitized logs without exposing keys.
- **429:** local per-IP limit or upstream API rate limit; retry later.
- **504:** network/timeout issue; retry later.
- **No reply:** ensure account has API billing/credits; ChatGPT subscription does not include API credits.

## Security, cost, limitations
**This public endpoint spends the project owner's API credits.** Set usage budgets/alerts and monitor API consumption; initially restrict access where possible. No user login, no billing controls, no distributed abuse prevention, and no guaranteed anonymity. The in-memory limiter resets on restart and is not shared across workers/instances; behind Render proxies the socket peer IP may be a shared proxy, so legitimate users may share one limit. We intentionally do not trust arbitrary forwarded headers. For production, use a trusted-proxy-aware IP policy, shared rate limiter, authentication, and edge protection. This basic protection cannot prevent determined abuse. Messages are sent to OpenAI to generate replies. No persistent server-side conversation history is implemented. Browser refresh clears the chat. Rich Markdown rendering is not implemented.

## Roadmap
Stabilize chat → improve observability/security → optional accounts → persistent chat history → long-term memory → configurable agents → voice I/O → wake-word privacy review → iPhone app.

## V0.2 welcome voice prototype
- The included synthesized robotic "Hello Stark" WAV at `static/audio/ultron-hello-stark.wav` is **not** the original film audio or an exact actor voice replica.
- On page load, the browser attempts to play the greeting while Voice is On. If browser autoplay policy blocks sound, use the visible Play greeting button.
- Voice On/Off is stored in this browser via localStorage. No extra TTS API calls required.
- Streaming chat replies are not implemented in this prototype.
