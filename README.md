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
