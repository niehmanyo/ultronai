#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ "${ULTRON_RUN_LIVE_TEST:-}" != I_UNDERSTAND_API_CHARGES ]]; then
  echo 'This performs a billable OpenAI model call. Set ULTRON_RUN_LIVE_TEST=I_UNDERSTAND_API_CHARGES after configuring the OpenAI model.'
  exit 2
fi
export DSH_HOME="${DSH_HOME:-$HOME/.ultron-dsh}"
cd "$ROOT/ultron-workspace"
exec npx --yes @deepseek-ai/dsh --profile headless '读取 AGENTS.md，并列出已调用的真实工具步骤。不要写入文件。'
