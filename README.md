# Ultron Agent V0.5 — DeepSeek Harness + OpenAI API

> Work in progress: **official dsh agent runtime** staged on this migration branch. This is not the public Render application. **Offline checks passed**; real npm download, OpenAI API invocation, and tool loop are not yet verified.

## Purpose

Replace custom FastAPI as the Agent Loop with the official `@deepseek-ai/dsh` runtime, while keeping **OpenAI API** as the model provider. Use native dsh Web UI, Agent Loop, tools, Skills and persisted Sessions. Do **not** switch to DeepSeek API.

## Local startup (macOS / Linux)

Requirements: Node.js **22.19+ or 24+**, npm, network access to npm registry and OpenAI Platform.

```bash
git clone --branch migration/deepseek-harness https://github.com/niehmanyo/ultronai.git
cd ultronai/harness
./start-local.sh
```

This starts official `npx @deepseek-ai/dsh web --no-open` from the isolated workspace. Use the authenticated URL printed in the terminal (normally localhost:3080). In **Settings → Models → Add model provider → Third-party → openai**, enter a private **OpenAI Platform API key**, save and select an available OpenAI model. Then **Choose workspace** and select `harness/ultron-workspace` to activate `AGENTS.md` and Skills.

For a complete **Chinese local deployment guide, safer startup checks, reproducible version selection, test scripts, and an archived V0.4 snapshot**, download the V0.5 deliverable ZIP from the associated ChatGPT project delivery. The branch-level `harness/docs/LOCAL_DEPLOYMENT_ZH.md` is a concise web copy.

## Architecture

```text
DSH Web UI → Cordis plugin composition / Agent Loop → Tool executions + approvals
                                      ├── OpenAI provider → OpenAI API
                                      ├── Session Event persistence under DSH_HOME
                                      └── Workspace Skills / approved memory file
```

## Security and current limitations

- Keep DSH local only. Do not point Render's public URL to an unrestricted tool-executing agent.
- Configure `DSH_HOME` outside Git. Never publish API keys, DSH credential files or authenticated launch URLs.
- Skills use explicit user-approved text memory, **not** automatic vector retrieval.
- Previous FastAPI Web UI, streaming, Hello Stark audio and PostgreSQL schema are separate and not automatically integrated into official dsh.
- Existing Render `main` branch deployment is unchanged.
- The official DSH is a developer preview: check and pin a published npm version before production use.

Upstream: https://github.com/deepseek-ai/deepseek-harness
Provider setup: https://deepseek-harness.github.io/deepseek-harness/en/guide/providers

## V0.5 Ultron branding and ChatGPT AI (local)

This feature is staged on `feature/ultron-branding-openai` pending user acceptance. It is **not merged** and not deployed to Render.

### Get this branch

```bash
git fetch origin
git switch feature/ultron-branding-openai
git pull --ff-only origin feature/ultron-branding-openai
cd harness
```

### 1. OpenAI model provider (OpenAI Platform, not ChatGPT subscription)

```bash
bash configure-openai.sh
```

When no Web profile patch exists, this creates a minimal `openai` provider named **ChatGPT AI** and references `OPENAI_API_KEY`. **It does not read or store secrets.** When a profile already exists, it refuses to overwrite it: use dsh **Settings → Models → Add model provider → Third-party → openai**, enter your OpenAI Platform key privately, save, and select an available OpenAI model (for example `gpt-4.1-mini`). The original configuration is preserved.

### 2. Local Ultron branding (Chrome)

In Chrome open `chrome://extensions`, enable Developer mode, press **Load unpacked**, and select `harness/branding/chrome-extension`. Refresh the local dsh Web UI on **http://127.0.0.1:3080**. This Chrome-only local extension changes tab title, favicon, visible brand text and adds an **original** Ultron-style SVG mark. It works on the locally running UI only; it does not modify the upstream dsh npm package. The built-in site branding can differ if upstream changes its DOM. Chrome extension permissions cover localhost hostnames, while its code explicitly refuses to operate outside port 3080.

### 3. Start and test

```bash
bash start-local.sh
```

Keep the terminal open. In Settings > Models select the OpenAI model, run a short task, and inspect usage on OpenAI Platform. Confirm no API key appears in Git. To revert the visual change, disable/remove the Chrome extension; to revert provider setup, restore the local dsh profile backup or edit the provider in Settings.

This is an interim branding adapter, not a separately compiled or fully rebranded dsh frontend. Do **not** expose the tool-enabled Agent to the public internet.


## VoiceOS V0.1a — Mac terminal voice core (feature branch)

This feature is developed on \`feature/voiceos-core-mvp\` and intentionally has **no sci-fi UI yet**. It connects the Mac microphone → OpenAI ASR → official DSH Python SDK Agent → macOS speech output, with playback interruption. It uses a **separate SDK runtime from DSH Web**, not a shared Web Session.

\`\`\`bash
git fetch origin
git switch feature/voiceos-core-mvp
cd harness
python3 -m venv .venv-voiceos
source .venv-voiceos/bin/activate
pip install -r voiceos/requirements.txt
python -m unittest discover -s voiceos/tests -v
python voiceos/core.py --doctor
# Supply OPENAI_API_KEY securely in this terminal; see the Chinese guide.
python voiceos/core.py --text "用中文说你好" --no-speech
python voiceos/core.py
\`\`\`

Read the complete [VoiceOS Chinese setup and acceptance guide](harness/docs/VOICEOS_CORE_V01_ZH.md) before testing. Python SDK's \`sdk\` profile requires a compatible OpenAI provider registration; working DSH Web credentials do not by themselves establish SDK-provider compatibility. Do not switch the provider to DeepSeek or claim real-world integration is validated without local Mac testing. No PR or Render deployment is part of this feature branch.
