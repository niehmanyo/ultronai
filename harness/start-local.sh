#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/ultron-workspace"
export DSH_HOME="${DSH_HOME:-$HOME/.ultron-dsh}"
mkdir -p "$DSH_HOME"
echo 'Private local DSH. Configure OpenAI provider in Settings > Models. Do not expose port publicly.'
exec npx --yes @deepseek-ai/dsh web --no-open
