#!/usr/bin/env python3
"""Install or remove the per-user macOS LaunchAgent for Ultron Remote."""
from __future__ import annotations
import argparse
import os
import plistlib
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LABEL = "com.ultron.remote-server"
PLIST = Path.home() / "Library" / "LaunchAgents" / f"{LABEL}.plist"
LOGS = Path.home() / ".ultron" / "logs"
PYTHON = ROOT.parent / ".venv-voiceos312" / "bin" / "python"


def launchctl(*args):
    return subprocess.run(["launchctl", *args], check=False, text=True,
                          capture_output=True, timeout=10)


def install():
    if sys.platform != "darwin":
        raise SystemExit("LaunchAgent installation is macOS-only.")
    if not PYTHON.is_file():
        raise SystemExit(f"Python environment not found: {PYTHON}\nCreate .venv-voiceos312 and install voiceos/requirements.txt first.")
    if not (ROOT / "remote_server.py").is_file():
        raise SystemExit("remote_server.py not found.")
    LOGS.mkdir(mode=0o700, parents=True, exist_ok=True)
    PLIST.parent.mkdir(parents=True, exist_ok=True)
    uid = os.getuid()
    payload = {
        "Label": LABEL,
        "ProgramArguments": [
            str(PYTHON), "-u", str(ROOT / "remote_server.py"),
            "--host", "127.0.0.1", "--port", "8766",
            "--workspace", str(ROOT.parent / "ultron-workspace"),
            "--dsh-home", str(Path.home() / ".ultron-dsh"),
        ],
        "WorkingDirectory": str(ROOT.parent),
        "RunAtLoad": True,
        "KeepAlive": {"SuccessfulExit": False},
        "ThrottleInterval": 10,
        "ProcessType": "Background",
        "StandardOutPath": str(LOGS / "remote-server.log"),
        "StandardErrorPath": str(LOGS / "remote-server-error.log"),
        "EnvironmentVariables": {
            "DSH_HOME": str(Path.home() / ".ultron-dsh"),
            "PATH": "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin",
        },
    }
    temporary = PLIST.with_suffix(".plist.tmp")
    temporary.write_bytes(plistlib.dumps(payload, fmt=plistlib.FMT_XML, sort_keys=True))
    os.chmod(temporary, 0o600)
    temporary.replace(PLIST)
    launchctl("bootout", f"gui/{uid}", str(PLIST))
    result = launchctl("bootstrap", f"gui/{uid}", str(PLIST))
    if result.returncode:
        raise SystemExit("launchctl bootstrap failed: " + (result.stderr.strip() or result.stdout.strip()))
    launchctl("kickstart", "-k", f"gui/{uid}/{LABEL}")
    print(f"Installed and started: {LABEL}")
    print(f"Logs: {LOGS}")
    print("Server is bound to 127.0.0.1:8766 only.")
    print("Use Tailscale Serve to publish it privately over your tailnet.")


def uninstall():
    if sys.platform != "darwin":
        raise SystemExit("LaunchAgent management is macOS-only.")
    uid = os.getuid()
    launchctl("bootout", f"gui/{uid}", str(PLIST))
    if PLIST.exists():
        PLIST.unlink()
    print(f"Removed: {LABEL}")


def status():
    result = launchctl("print", f"gui/{os.getuid()}/{LABEL}")
    print(result.stdout if result.returncode == 0 else "Ultron Remote LaunchAgent is not loaded.")
    if result.stderr and result.returncode:
        print(result.stderr.strip())


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("install", "uninstall", "status"))
    args = parser.parse_args()
    {"install": install, "uninstall": uninstall, "status": status}[args.action]()
