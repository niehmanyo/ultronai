# Ultron: DeepSeek Harness (DSH) + OpenAI migration

## Branch status
This is an **isolated experimental branch**, not the public V0.3 production deployment. It uses the **official** `deepseek-harness-sdk` and Cordis `sdk` profile, not a simulated agent loop.

### Request path
Private Browser -> `agent_app.py` (login gate + SSE progress) -> `dsh_bridge.py` -> `DeepSeekHarness(provider="openai", profile="sdk")` -> DSH model adapter `llm-pi-ai` configured in `dsh/cordis.patch.yml` -> existing OpenAI API key.

### Files
- `agent_app.py`: independent FastAPI preview, health, login, run/continue, sanitized activity SSE.
- `dsh_security.py`: 16+ character owner password, 32+ character HMAC secret, secure HttpOnly cookie, Origin check, login attempt limit.
- `dsh_bridge.py`: official DeepSeekHarness runtime, session resume, model selection.
- `dsh/cordis.patch.yml`: OpenAI provider route. No API key in source control.
- `static/agent.html` and `static/agent.js`: private UI with existing Hello Stark asset.
- `requirements-dsh.txt`: official SDK distribution.

### Setup (isolated test server only)
1. Install dependencies with `pip install -r requirements-dsh.txt` in Python 3.10+ on supported Linux x64/arm64 or macOS arm64.
2. Set `OPENAI_API_KEY` with the **same OpenAI key you already use**, `OPENAI_MODEL=gpt-4.1-mini`, plus randomly generated `ULTRON_ADMIN_PASSWORD` (16+ chars) and `ULTRON_SESSION_SECRET` (32+ chars) using private environment variables. Do **not** put real values in git.
3. Provide persistent, isolated `ULTRON_DSH_HOME` and disposable `ULTRON_DSH_WORKSPACE`, and verify the full DSH `sdk` plugin configuration using `DSH_HOME=/your/isolated/home dsh --profile sdk --dump-config`. Verify the `llm-pi-ai` provider is `openai`.
4. Start `uvicorn agent_app:app --host 127.0.0.1 --port 8001` inside the sandbox.
5. **Important:** Agent runs are disabled until a tool sandbox and permissions are reviewed. Only in a disposable test environment, set `ULTRON_DSH_UNSAFE_AGENT_PREVIEW=I_ACCEPT_TOOL_RISK` to allow DSH execution.
6. Confirm login protection, an OpenAI request, DSH tool lifecycle events, and session resume.

### Security and product limitations
- The DSH `sdk` profile can mount shell/file tools. Passwords alone are insufficient as a sandbox. Tool processes may read secrets and filesystem from their host. **Do not set the unsafe preview flag on a publicly reachable deployment.**
- The Python SDK's durable `assistant/message` notifications are not guaranteed real-time per-token deltas; progress SSE is truthful and the final answer arrives when the step commits. Original V0.3 streaming chat remains available on the main branch.
- DSH session data stored only on Render's ephemeral filesystem is not durable. A persistent disk or external session backend must be tested before Memory rollout.
- This migration has been statically validated and local mocked integration/auth tests were run; **a live DSH runtime + OpenAI end-to-end smoke test has not passed in the assistant environment** because the SDK distribution could not be installed here. No production switch has been made.
- V0.4 private-history work is on the separate `feature/v0.4-private-history` branch and has not been deployed. Do not merge it blindly with this branch.

### Production readiness gate
Sandbox/permissions; secret separation; persistent data volume; per-run cost budget; cancellation; SDK pinning; real event protocol test; OpenAI model tool-calling compatibility; end-to-end browser and recovery tests. Only then consider replacing the live Render start command.

Official resources:
- https://github.com/deepseek-ai/deepseek-harness
- https://deepseek-harness.github.io/deepseek-harness/en/guide/python-sdk
- https://deepseek-harness.github.io/deepseek-harness/en/guide/providers
