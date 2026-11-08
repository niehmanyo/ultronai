"""Offline security and validation tests for Ultron Remote."""
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("remote_server", ROOT / "remote_server.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class TestRemoteServer(unittest.TestCase):
    def test_token_is_persisted_and_long(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "nested" / "token"
            with patch.object(module, "TOKEN_PATH", target):
                first = module.load_or_create_token()
                second = module.load_or_create_token()
            self.assertEqual(first, second)
            self.assertGreaterEqual(len(first), 40)
            if os.name == "posix":
                self.assertEqual(target.stat().st_mode & 0o777, 0o600)

    def test_session_id_validation(self):
        valid = ["ultron-remote-12345678", "Session_123456"]
        invalid = ["", "short", "../etc/passwd", "contains spaces", "a" * 81, None]
        for item in valid:
            self.assertIsNotNone(module.SESSION_RE.fullmatch(item))
        for item in invalid:
            self.assertIsNone(module.SESSION_RE.fullmatch(item))

    def test_message_limits(self):
        self.assertEqual(module.MAX_MESSAGE, 12000)
        self.assertLess(module.MAX_BODY, 32768)

    def test_token_comparison_requires_bearer(self):
        app = module.RemoteApplication(object(), "correct-token")
        class Request:
            def __init__(self, value):
                self.headers = {"Authorization": value}
        self.assertTrue(app.authorized(Request("Bearer correct-token")))
        self.assertFalse(app.authorized(Request("correct-token")))
        self.assertFalse(app.authorized(Request("Bearer wrong-token")))
        self.assertFalse(app.authorized(Request("")))


if __name__ == "__main__":
    unittest.main()
