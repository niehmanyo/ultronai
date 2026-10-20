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

# DeepSeek Harness uses HTTP_PROXY / HTTPS_PROXY, not macOS System Settings.
# Never replace an explicitly supplied proxy. Auto-detect only a loopback HTTP
# proxy that macOS already has enabled; never adopt nonlocal or credentialed URLs.
# Set ULTRON_PROXY_AUTO=0 to disable macOS proxy discovery.
if [[ "${ULTRON_PROXY_AUTO:-1}" != "0" && "$(uname -s)" == "Darwin" ]] \
   && [[ -z "${HTTPS_PROXY:-}" && -z "${https_proxy:-}" && -z "${ALL_PROXY:-}" && -z "${all_proxy:-}" ]]; then
  if command -v scutil >/dev/null 2>&1; then
    mac_proxy="$(scutil --proxy 2>/dev/null || true)"
    enabled="$(printf '%s\n' "$mac_proxy" | awk '$1=="HTTPSEnable" && $2==":" {print $3;exit}')"
    host="$(printf '%s\n' "$mac_proxy" | awk '$1=="HTTPSProxy" && $2==":" {print $3;exit}')"
    port="$(printf '%s\n' "$mac_proxy" | awk '$1=="HTTPSPort" && $2==":" {print $3;exit}')"
    if [[ "$enabled" == "1" && ( "$host" == "127.0.0.1" || "$host" == "localhost" ) \
          && "$port" =~ ^[0-9]{1,5}$ ]] && (( 10#$port > 0 && 10#$port <= 65535 )); then
      if (echo >/dev/tcp/127.0.0.1/"$port") >/dev/null 2>&1; then
        export HTTPS_PROXY="http://127.0.0.1:$port"
        export HTTP_PROXY="${HTTP_PROXY:-${http_proxy:-$HTTPS_PROXY}}"
        echo "[Ultron] Using macOS local HTTP proxy for dsh: 127.0.0.1:$port"
      else
        echo "[Ultron] macOS proxy 127.0.0.1:$port is configured but not listening; OpenAI may be unreachable." >&2
      fi
    fi
  fi
fi

# DSH bypasses loopback, and these exceptions also protect ordinary subprocesses.
export NO_PROXY="${NO_PROXY:-${no_proxy:-localhost,127.0.0.1,::1}}"
echo "[Ultron] Starting dsh using Node $NODE_VERSION. Leave this terminal open."
echo "[Ultron] Local profile: $DSH_HOME"
if [[ -n "${HTTPS_PROXY:-}" ]]; then echo "[Ultron] HTTPS proxy configured (value not printed)."; fi
echo '[Ultron] Optional: run "bash ../configure-openai.sh" from this workspace.'
exec npx --yes @deepseek-ai/dsh web --no-open
