"""Offline checks of desktop app sources (do not compile the macOS binary).

The actual app must be built and verified with swiftc on macOS.
"""
from pathlib import Path
import subprocess
import unittest

DESKTOP = Path(__file__).resolve().parents[1]
SWIFT = DESKTOP / "UltronDesktop.swift"
BUILDER = DESKTOP / "build-macos-app.sh"


class TestDesktopScaffold(unittest.TestCase):
    def test_shell_script_syntax(self):
        result = subprocess.run(["bash", "-n", str(BUILDER)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_native_window_keychain_and_safe_runtime_wiring(self):
        script = SWIFT.read_text(encoding="utf8")
        for required in [
            "WKWebView", "NSApplication", "NSStatusBar", "SecItemCopyMatching",
            "SecItemAdd", "SecItemUpdate", "NSecureTextField",
            "OPENAI_API_KEY", "processIdentifier", "SIGINT",
            "FileHandle.nullDevice", "--hands-free", "--dashboard",
            "--dashboard-port", "UltronHarnessPath", "UltronPythonPath",
            'url.host == "127.0.0.1"', "Pause Microphone",
            "applicationShouldHandleReopen",
        ]:
            with self.subTest(required=required):
                self.assertIn(required, script)
        self.assertNotIn("sk-proj-", script)
        self.assertNotIn("api.openai.com", script)

    def test_installer_uses_existing_venv_not_terminal_at_runtime(self):
        installer = BUILDER.read_text(encoding="utf8")
        self.assertIn(".venv-voiceos312/bin/python", installer)
        self.assertIn('"$HOME/Applications/Ultron VoiceOS.app"', installer)
        self.assertIn("CFBundleExecutable", installer)
        self.assertIn("NSMicrophoneUsageDescription", installer)
        self.assertIn("swiftc", installer)
        self.assertIn('open "$APP_DIR"', installer)
        self.assertNotIn("open -a Terminal", installer)


if __name__ == "__main__":
    unittest.main()
