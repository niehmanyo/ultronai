# Ultron on the official DeepSeek Harness

This is a staged migration to **official DeepSeek Harness (dsh)**, *not* a new Python Agent Loop. It does not switch the model provider to DeepSeek: use the built-in **OpenAI** third-party provider.

## Local private startup

With recent Node.js:

```sh
cd harness/ultron-workspace
export DSH_HOME="$HOME/.ultron-dsh"
npx --yes @deepseek-ai/dsh web --no-open
```

Open the local DSH UI (normally http://127.0.0.1:3080). Under Settings → Models → Add model provider choose **openai**, provide your **OpenAI API** key privately, and select an available model such as gpt-4.1-mini. Choose the **harness/ultron-workspace** workspace to enable the AGENTS.md instructions and .dsh/skills.

The DSH app is a tool-executing agent and **must not** be exposed publicly without strong authentication, sandboxed tool execution, durable state, HTTPS and cost controls. Do **not** replace the running Render FastAPI service with an unauthenticated dsh process.

Old FastAPI files remain in the repository for rollback. The previous V0.4 implementation has NOT been deployed; a complete V0.4 snapshot and a read-only PostgreSQL exporter are available in the separately delivered migration ZIP. DSH's session event history is not an automatic import of old PostgreSQL chats. Native long-term vector memory and the custom Hello Stark voice UI are not yet integrated.

Upstream: https://github.com/deepseek-ai/deepseek-harness
Docs: https://deepseek-harness.github.io/deepseek-harness/en/guide/providers

This branch is intentionally not deployed. Pin and test a real DSH release before production cutover.
