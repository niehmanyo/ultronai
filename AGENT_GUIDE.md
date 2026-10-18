# Ultron Agent Guide

## Identity and goal
奥创计划 Ultron / Ultron Web is currently a publicly accessible **text-only** personal AI chat website. OpenAI Responses API, FastAPI, vanilla JS, GitHub source, Render deployment target. It is not yet a persistent personal assistant.

## Architecture
Browser `static/app.js` holds tab-local message array → `POST /api/chat` → FastAPI `main.py` validates and limits requests → official OpenAI Python SDK `responses.create` → sanitized reply → browser display. Render serves the ASGI app. API key is server-side only.

## Status
**Implemented in source:** UI, context transmission, request schema validation, basic in-memory rate limiting, body/message/history/output limits, `/health`, OpenAI integration, config, Render Blueprint, mock tests.
**Not implemented:** rich Markdown formatting, accounts, database, persistent memory, voice, mobile native app, shared rate limiting, cost quotas, cross-device sync.
**Unverified until performed:** live OpenAI request, real Render deployment, production proxy IP behavior, high-load resilience.

## Files and change locations
- `main.py`: API, security limits, model settings, upstream error mapping.
- `static/index.html`: markup, textarea maxlength.
- `static/style.css`: appearance, responsive rules.
- `static/app.js`: chat state, browser behavior, safe rendering.
- `tests/test_app.py`: mocked backend tests.
- `requirements.txt`: Python dependencies.
- `.env.example`: example settings; `.gitignore`: secret protection.
- `render.yaml`: build/start/health and environment.
- `README.md`: user and deployment instructions.
- `ULTRON_AGENT_HANDOFF.md`: original handoff requirements.

## Development constraints
Read the repository and Git history before edits. Keep OpenAI as the provider, use Responses API, preserve the lightweight architecture, never hardcode secrets, run tests after changes, update docs/config/test cases, and do not claim untested integrations or roadmap features are complete.

## Next steps
1. Stabilize and deploy current web chat.
2. Improve security and error handling, including trusted proxy handling and global abuse limits.
3. Add authentication only if required.
4. Add server-side persistent chat history.
5. Design explicit opt-in long-term memory.
6. Make agent behavior configurable.
7. Explore voice input/output.
8. Investigate wake-word privacy and OS restrictions.
9. Design native iPhone app.

## New agent onboarding
Read `AGENT_GUIDE.md` and `README.md`, inspect actual files and Git history, confirm branch and environment, run tests, enumerate implemented vs missing vs unverified, evaluate requested change impact, implement incrementally, and update tests, docs and changelog. Never assume this guide proves a deployment happened.
