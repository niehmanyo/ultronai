"""Offline tests for the localhost VoiceOS cognition dashboard."""
import importlib.util
import json
from pathlib import Path
import unittest
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("voice_dashboard", ROOT / "dashboard.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class TestDashboard(unittest.TestCase):
    def test_hub_stores_events_and_replays_to_subscribers(self):
        hub = module.EventHub()
        hub.emit("transcribing", detail="Transcribing", asr_ms=243)
        sink = hub.subscribe()
        event = sink.get_nowait()
        self.assertEqual(event["stage"], "transcribing")
        self.assertEqual(event["metrics"]["asr_ms"], 243)
        hub.emit("thinking", detail="Agent working")
        self.assertEqual(sink.get_nowait()["stage"], "thinking")
        hub.unsubscribe(sink)

    def test_local_readonly_dashboard_serves_html(self):
        dash = module.Dashboard(port=0)
        try:
            url = dash.start()
            self.assertTrue(url.startswith("http://127.0.0.1:"))
            with urlopen(url, timeout=5) as response:
                html = response.read().decode()
                self.assertIn("COGNITIVE CORTEX", html)
                self.assertIn("neural3d", html)
                self.assertIn("cortex3d.js", html)
            with urlopen(url + "cortex3d.js", timeout=5) as js_response:
                script = js_response.read().decode()
                self.assertIn("webgl", script)
                self.assertIn("UltronNeural", script)
                self.assertIn("text/html", response.headers["Content-Type"])
            with self.assertRaises(Exception):
                urlopen(url + "missing", timeout=5)
        finally:
            dash.stop()

    def test_audio_levels_are_transient_and_normalized(self):
        dash = module.Dashboard(port=0)
        old = dash.hub.subscribe()
        dash.audio_level(5.0, turn=3)
        event = old.get_nowait()
        self.assertEqual(event["stage"], "audio_level")
        self.assertEqual(event["metrics"]["level"], 1.0)
        dash.hub.unsubscribe(old)
        replay = dash.hub.subscribe()
        self.assertTrue(replay.empty())
        dash.hub.unsubscribe(replay)

    def test_event_json_is_serializable(self):
        hub = module.EventHub()
        event = hub.emit("completed", reply="Systems nominal", turn_ms=823)
        parsed = json.loads(json.dumps(event))
        self.assertEqual(parsed["metrics"]["reply"], "Systems nominal")


if __name__ == "__main__":
    unittest.main()
