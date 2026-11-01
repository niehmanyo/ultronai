#!/usr/bin/env bash
# Install a locally built Finder/Dock-launchable macOS desktop shell.
# Requires the already working VoiceOS Python venv and project checkout.
set -euo pipefail

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "This build script requires macOS." >&2
  exit 2
fi
if ! command -v swiftc >/dev/null 2>&1; then
  echo "Install Xcode Command Line Tools: xcode-select --install" >&2
  exit 2
fi
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
HARNESS="$(cd "$SCRIPT_DIR/.." && pwd)"
PYTHON_BIN="$HARNESS/.venv-voiceos312/bin/python"
if [[ -n "$ULTRON_PYTHON" ]]; then PYTHON_BIN="$ULTRON_PYTHON"; fi
if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "Missing VoiceOS Python: $PYTHON_BIN" >&2
  echo "Set ULTRON_PYTHON=/absolute/path/to/working/python if necessary." >&2
  exit 2
fi
PYTHON_BIN="$("$PYTHON_BIN" -c 'import os,sys; print(os.path.abspath(sys.executable))')"
if ! "$PYTHON_BIN" -c 'import openai,sounddevice,numpy,deepseek_harness' >/dev/null 2>&1; then
  echo "VoiceOS dependencies missing in $PYTHON_BIN" >&2
  exit 2
fi
if [[ ! -f "$HARNESS/voiceos/core.py" || ! -f "$HARNESS/voiceos/dashboard.html" || ! -d "$HARNESS/ultron-workspace" ]]; then
  echo "VoiceOS core, assets or workspace missing from $HARNESS" >&2
  exit 2
fi
APP_DIR="$HOME/Applications/Ultron VoiceOS.app"
if [[ -n "$ULTRON_APP_DEST" ]]; then APP_DIR="$ULTRON_APP_DEST"; fi
if [[ "$APP_DIR" != /* ]]; then
  echo "ULTRON_APP_DEST must be an absolute path." >&2
  exit 2
fi
if [[ -e "$APP_DIR" && ! -f "$APP_DIR/Contents/Info.plist" ]]; then
  echo "Refusing to overwrite unrelated path: $APP_DIR" >&2
  exit 2
fi
mkdir -p "$(dirname "$APP_DIR")"
TEMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TEMP_DIR"' EXIT
BUILD_APP="$TEMP_DIR/Ultron VoiceOS.app"
mkdir -p "$BUILD_APP/Contents/MacOS" "$BUILD_APP/Contents/Resources"
"$PYTHON_BIN" - "$BUILD_APP/Contents/Info.plist" "$HARNESS" "$PYTHON_BIN" <<'PY'
import plistlib
import sys
from pathlib import Path
path, root, python = sys.argv[1:]
info = {
    "CFBundleDevelopmentRegion": "en",
    "CFBundleExecutable": "UltronVoiceOS",
    "CFBundleIdentifier": "com.ultron.voiceos.desktop",
    "CFBundleInfoDictionaryVersion": "6.0",
    "CFBundleName": "Ultron VoiceOS",
    "CFBundleDisplayName": "Ultron VoiceOS",
    "CFBundlePackageType": "APPL",
    "CFBundleShortVersionString": "0.1.0",
    "CFBundleVersion": "1",
    "LSMinimumSystemVersion": "14.0",
    "NSHighResolutionCapable": True,
    "NSMicrophoneUsageDescription": "Ultron needs microphone access for hands-free voice requests.",
    "UltronHarnessPath": root,
    "UltronPythonPath": python,
}
with Path(path).open("wb") as output:
    plistlib.dump(info, output)
PY
echo "[Ultron Desktop] Compiling native Cocoa/WebKit app..."
swiftc -O -framework Cocoa -framework WebKit -framework Security \
  "$SCRIPT_DIR/UltronDesktop.swift" -o "$BUILD_APP/Contents/MacOS/UltronVoiceOS"
chmod 755 "$BUILD_APP/Contents/MacOS/UltronVoiceOS"
if command -v codesign >/dev/null 2>&1; then
  codesign --force --sign - "$BUILD_APP" >/dev/null
fi
if [[ -d "$APP_DIR" ]]; then
  BACKUP="$APP_DIR.old.$(date +%Y%m%d%H%M%S)"
  mv "$APP_DIR" "$BACKUP"
  echo "[Ultron Desktop] Backed up previous installation to $BACKUP"
fi
mv "$BUILD_APP" "$APP_DIR"
echo "[Ultron Desktop] Installed $APP_DIR"
echo "[Ultron Desktop] This is NOT a standalone distribution: keep $HARNESS and $PYTHON_BIN in place."
echo "[Ultron Desktop] First launch will prompt for an OpenAI API key and store it in Keychain."
open "$APP_DIR"
