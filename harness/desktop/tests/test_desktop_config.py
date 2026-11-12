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

    def test_v08_mini_orb_and_hotkey(self):
        main = SWIFT.read_text(encoding="utf8")
        orb = (DESKTOP / "UltronOrb.swift").read_text(encoding="utf8")
        hotkey = (DESKTOP / "UltronHotkey.swift").read_text(encoding="utf8")
        html = (DESKTOP / "Orb.html").read_text(encoding="utf8")
        self.assertIn("UltronOrb(onOpen:", main)
        self.assertIn("UltronHotkey(callback:", main)
        self.assertIn("Start Listening", main)
        self.assertIn("MICROPHONE OFF", main)
        self.assertIn("STARTUP TIMED OUT", main)
        self.assertIn("stopping = true", main)
        self.assertIn("SIGINT", main)
        self.assertIn("SIGKILL", main)
        self.assertIn("WKWebView", orb)
        self.assertIn(".nonactivatingPanel", orb)
        self.assertIn("GetEventDispatcherTarget", hotkey)
        self.assertIn("RegisterEventHotKey", hotkey)
        self.assertIn("UnregisterEventHotKey", hotkey)
        self.assertIn("canvas", html)
        self.assertIn("requestAnimationFrame", html)

    def test_installer_uses_existing_venv_not_terminal_at_runtime(self):
        installer = BUILDER.read_text(encoding="utf8")
        self.assertIn(".venv-voiceos312/bin/python", installer)
        self.assertIn('"$HOME/Applications/Ultron VoiceOS.app"', installer)
        self.assertIn("CFBundleExecutable", installer)
        self.assertIn("NSMicrophoneUsageDescription", installer)
        self.assertIn("swiftc", installer)
        self.assertIn("UltronOrb.swift", installer)
        self.assertIn("UltronHotkey.swift", installer)
        self.assertIn("Orb.html", installer)
        self.assertIn("CFBundleShortVersionString", installer)
        self.assertIn('open "$APP_DIR"', installer)
        self.assertNotIn("open -a Terminal", installer)


if __name__ == "__main__":
    unittest.main()
