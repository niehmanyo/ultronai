"""Offline tests for the official DSH session-event visualization adapter."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("tool_graph", ROOT / "tool_graph.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def notice(event_type, data):
    return SimpleNamespace(method="session.event", payload={
        "sessionId": "test", "event": {"type": event_type, "data": data}})


class TestToolGraph(unittest.TestCase):
    def setUp(self):
        self.rows = []
        self.observer = module.ToolGraphObserver(lambda stage, **kw: self.rows.append((stage, kw)), turn=7)

    def test_call_and_result_match_without_arguments_or_content(self):
        self.observer(notice("tool/call", {"callId": "private-19", "name": "search",
                                            "arguments": '{"password":"do-not-emit"}'}))
        self.observer(notice("tool/result", {"message": {"source": {"callId": "private-19"},
                                              "content": [{"type": "text", "text": "PRIVATE OUTPUT"}],
                                              "isError": False}}))
        self.assertEqual([x[1]["tool_state"] for x in self.rows], ["running", "completed"])
        self.assertEqual([x[1]["tool_id"] for x in self.rows], [1, 1])
        self.assertEqual(self.rows[0][1]["tool_name"], "search")
        self.assertNotIn("do-not-emit", str(self.rows))
        self.assertNotIn("PRIVATE OUTPUT", str(self.rows))
        self.assertNotIn("private-19", str(self.rows))

    def test_errors_and_unknown_completion(self):
        self.observer(notice("tool/call", {"callId": "1", "name": "execute", "arguments": "{}"}))
        self.observer(notice("tool/result", {"message": {"source": {"callId": "1"}, "isError": True}}))
        self.assertEqual(self.rows[-1][1]["tool_state"], "error")
        self.observer(notice("tool/call", {"callId": "2", "name": "fetch", "arguments": "{}"}))
        self.observer.finish()
        self.assertEqual(self.rows[-1][1]["tool_state"], "unknown")

    def test_does_not_invent_tools_from_irrelevant_notifications(self):
        self.observer(SimpleNamespace(method="session.status", payload={"status": "busy"}))
        self.observer(notice("assistant/message", {"text": "secret thoughts"}))
        self.observer(notice("tool/result", {"message": {"source": {"callId": "not-seen"}}}))
        self.assertEqual(self.rows, [])

    def test_limit_and_sanitize_names(self):
        obs = module.ToolGraphObserver(lambda stage, **kw: self.rows.append((stage, kw)), turn=4, max_nodes=1)
        obs(notice("tool/call", {"callId": "1", "name": "<script>alert(1)</script>", "arguments": "{}"}))
        obs(notice("tool/call", {"callId": "2", "name": "another", "arguments": "{}"}))
        self.assertEqual(len(self.rows), 1)
        self.assertEqual(self.rows[0][1]["tool_name"], "tool")


if __name__ == "__main__":
    unittest.main()
