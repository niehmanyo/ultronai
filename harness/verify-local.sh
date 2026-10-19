#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
test -f "$ROOT/ultron-workspace/AGENTS.md"
test -f "$ROOT/ultron-workspace/.dsh/skills/memory/SKILL.md"
test -f "$ROOT/ultron-workspace/.dsh/skills/task-execution/SKILL.md"
bash -n "$ROOT/start-local.sh"
node -v
npm -v
echo "PASS: workspace files, launcher syntax and runtime presence"
echo "NOT VERIFIED: npm availability, OpenAI API, dsh tool execution."
