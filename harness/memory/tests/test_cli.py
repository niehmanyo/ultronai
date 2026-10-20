#!/usr/bin/env python3
"""Offline integration tests for Ultron SQLite Memory CLI (stdlib only)."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

CLI = Path(__file__).resolve().parents[1] / "cli.py"


class MemoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.env = dict(os.environ, DSH_HOME=self.tmp.name)

    def run_cli(self, *args, code=0):
        cmd = [sys.executable, str(CLI), *args]
        cp = subprocess.run(cmd, env=self.env, text=True, capture_output=True, timeout=20)
        self.assertEqual(cp.returncode, code, (cp.stdout, cp.stderr))
        return json.loads(cp.stdout)

    def propose(self, text):
        return self.run_cli("propose", "--action", "add", "--text", text)["proposal_id"]

    def test_no_memory_before_approval(self):
        self.propose("喜欢精简的中文技术解答")
        self.assertEqual([], self.run_cli("search", "精简"))
        self.assertEqual(1, len(self.run_cli("proposals")))

    def test_approval_survives_new_process(self):
        pid = self.propose("偏好先中文再讲解技术术语")
        self.run_cli("approve", "--proposal-id", pid)
        row = self.run_cli("search", "技术")[0]
        self.assertEqual("偏好先中文再讲解技术术语", row["body"])
        # Each run_cli starts an entirely new process, proving disk persistence.
        self.assertEqual(row["id"], self.run_cli("list")[0]["id"])
        self.assertEqual([], self.run_cli("proposals"))

    def test_rejection(self):
        pid = self.propose("爱吃菠萝")
        self.run_cli("reject", "--proposal-id", pid)
        self.assertEqual([], self.run_cli("list"))
        self.run_cli("approve", "--proposal-id", pid, code=1)

    def test_update_requires_separate_approval(self):
        self.run_cli("approve", "--proposal-id", self.propose("喜欢简短回答"))
        mid = self.run_cli("list")[0]["id"]
        proposal = self.run_cli("propose", "--action", "update", "--id", mid,
                                "--text", "喜欢详细回答")["proposal_id"]
        self.assertEqual("喜欢简短回答", self.run_cli("list")[0]["body"])
        self.run_cli("approve", "--proposal-id", proposal)
        self.assertEqual("喜欢详细回答", self.run_cli("list")[0]["body"])

    def test_forget_requires_approval(self):
        self.run_cli("approve", "--proposal-id", self.propose("临时偏好"))
        mid = self.run_cli("list")[0]["id"]
        pid = self.run_cli("propose", "--action", "forget", "--id", mid)["proposal_id"]
        self.assertEqual(1, len(self.run_cli("list")))
        self.run_cli("approve", "--proposal-id", pid)
        self.assertEqual([], self.run_cli("list"))

    def test_secret_refused(self):
        self.run_cli("propose", "--text", "api_key: secret", code=1)
        self.assertEqual([], self.run_cli("proposals"))

    def test_no_git_storage(self):
        self.propose("某个项目使用 Python")
        self.assertTrue((Path(self.tmp.name) / "memory" / "ultron.sqlite3").exists())
        self.assertFalse((CLI.parent / "ultron.sqlite3").exists())

    def test_scope(self):
        pid = self.run_cli("propose", "--text", "这个项目用 sqlite", "--scope", "workspace")["proposal_id"]
        self.run_cli("approve", "--proposal-id", pid)
        self.assertEqual([], self.run_cli("search", "sqlite", "--scope", "global"))
        self.assertEqual(1, len(self.run_cli("search", "sqlite", "--scope", "workspace")))


if __name__ == "__main__":
    unittest.main(verbosity=2)
