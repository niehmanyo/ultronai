#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE="$ROOT/ultron-workspace"
export DSH_HOME="${DSH_HOME:-$HOME/.ultron-dsh}"
LOG_DIR="${ULTRON_LOG_DIR:-$HOME/.ultron-dsh/logs}"
mkdir -p "$DSH_HOME" "$LOG_DIR"
chmod 700 "$DSH_HOME" "$LOG_DIR" || true

if ! command -v node >/dev/null || ! command -v npm >/dev/null || ! command -v npx >/dev/null; then
  echo '[Ultron] ERROR: Node.js, npm and npx are required.' >&2
  exit 2
fi
NODE_VERSION="$(node -p 'process.versions.node')"
echo "[Ultron] Node: $NODE_VERSION | npm: $(npm -v) | npx: $(npx --version)"
if ! node -e 'const [maj,min]=process.versions.node.split(".").map(Number);process.exit(((maj===22&&min>=19)||maj>=24) ? 0 : 1)'; then
  echo '[Ultron] ERROR: DSH requires Node 22.19+ or 24+. Upgrade Node and rerun.' >&2
  exit 2
fi
echo "[Ultron] DSH_HOME: $DSH_HOME"
echo "[Ultron] Workspace: $WORKSPACE"
echo '[Ultron] Starting official dsh. Keep this terminal open while using the Web UI.'
echo '[Ultron] Do not share an authenticated URL or credentials from its output.'

cd "$WORKSPACE"
LOGFILE="$LOG_DIR/startup-$(date +%Y%m%d-%H%M%S).log"
echo "[Ultron] Startup log: $LOGFILE"
set +e
npx --yes @deepseek-ai/dsh web --no-open 2>&1 | tee "$LOGFILE"
status=${PIPESTATUS[0]}
set -e

if [ "$status" -eq 0 ]; then
  echo '[Ultron] DSH process exited without an error code; it is no longer serving the Web UI.' >&2
else
  echo "[Ultron] DSH exited with code $status." >&2
fi
echo '[Ultron] Diagnostics (run without exposing tokens):' >&2
echo '  node -v' >&2
echo '  npm view @deepseek-ai/dsh version engines bin --json' >&2
echo '  npm config get registry' >&2
echo '  npm cache ls @deepseek-ai/dsh' >&2
echo '  lsof -nP -iTCP:3080 -sTCP:LISTEN' >&2
echo "[Ultron] Inspect locally: $LOGFILE (redact tokens/keys before sharing)" >&2
exit 1
