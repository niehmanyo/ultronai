#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT/ultron-workspace"
export DSH_HOME="${DSH_HOME:-$HOME/.ultron-dsh}"
mkdir -p "$DSH_HOME"
chmod 700 "$DSH_HOME" 2>/dev/null || true
if ! command -v node >/dev/null || ! command -v npm >/dev/null || ! command -v npx >/dev/null; then
  echo '[Ultron] Install Node.js (22.19+ or 24+) and npm first.' >&2
  exit 2
fi
NODE_VERSION="$(node -p 'process.versions.node')"
if ! node -e 'const [major,minor]=process.versions.node.split(".").map(Number);process.exit((major===22&&minor>=19)||major>=24?0:1)'; then
  echo "[Ultron] Unsupported Node $NODE_VERSION; need Node 22.19+ or 24+." >&2
  exit 2
fi
echo "[Ultron] Starting dsh using Node $NODE_VERSION. Leave this terminal open."
echo "[Ultron] Local profile: $DSH_HOME"
echo '[Ultron] Optional: run "bash ../configure-openai.sh" from this workspace.'
exec npx --yes @deepseek-ai/dsh web --no-open
