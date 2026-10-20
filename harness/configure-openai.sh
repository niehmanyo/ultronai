#!/usr/bin/env bash
set -euo pipefail
export DSH_HOME="${DSH_HOME:-$HOME/.ultron-dsh}"
PROFILE="${ULTRON_PROFILE_NAME:-web}"
FILE="$DSH_HOME/profiles/$PROFILE/cordis.patch.yml"
mkdir -p "$(dirname "$FILE")"
chmod 700 "$DSH_HOME" "$(dirname "$FILE")" 2>/dev/null || true
if [[ -f "$FILE" ]]; then
  echo "[Ultron] Existing dsh profile detected: $FILE"
  echo "[Ultron] To avoid erasing existing providers, configure in Web UI:"
  echo "  Settings > Models > Add model provider > Third-party > openai"
  echo "  Enter your OpenAI Platform key in the private UI and save."
  echo "  Select an OpenAI model (e.g. gpt-4.1-mini) from model picker."
  echo "[Ultron] Your existing file was NOT modified."
  exit 0
fi
cat > "$FILE" <<'YAML'
- id: llm-pi-ai
  config:
    providers:
      openai:
        displayName: ChatGPT AI
        apiKeyEnv: OPENAI_API_KEY
YAML
chmod 600 "$FILE"
echo "[Ultron] Registered ChatGPT AI (OpenAI provider) in $FILE"
echo "[Ultron] Now open Settings > Models to enter your key privately and select a model."
echo "[Ultron] No API key is read, printed, or stored by this script."
