"""Offline tests; no microphone, model credentials, or SDK download required."""
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
import wave
from unittest.mock import patch, MagicMock

MODULE = Path(__file__).resolve().parents[1] / "core.py"
spec = importlib.util.spec_from_file_location("voiceos_core", MODULE)
core = importlib.util.module_from_spec(spec)
spec.loader.exec_module(core)


class TestVoiceOS(unittest.TestCase):
    def test_parser_default(self):
        with patch.dict(os.environ, {}, clear=True):
            args = core.build_parser().parse_args([])
        self.assertEqual(args.provider, "openai")
        self.assertEqual(args.profile, "sdk")
        self.assertEqual(args.sdk_patch.name, "openai.patch.yml")
        self.assertTrue(args.sdk_patch.is_file())
        self.assertEqual(args.stt_model, "gpt-4o-mini-transcribe")

    def test_patch_references_env_not_secret(self):
        text = (MODULE.parent / "openai.patch.yml").read_text()
        self.assertIn("apiKeyEnv: OPENAI_API_KEY", text)
        self.assertIn("id: llm-pi-ai", text)
        self.assertNotIn("sk-proj-", text)

    def test_agent_response(self):
        agent = MagicMock()
        agent.run.return_value.final_response = "你好！"
        self.assertEqual(core.run_agent(agent, "你好", "session-1"), "你好！")
        agent.run.assert_called_once_with("你好", session_id="session-1")

    def test_transcribe_uses_audio_file(self):
        client = MagicMock()
        client.audio.transcriptions.create.return_value.text = "  你好 Ultron  "
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "audio.wav"
            with wave.open(str(path), "wb") as f:
                f.setnchannels(1)
                f.setsampwidth(2)
                f.setframerate(16000)
                f.writeframes(b"\x00\x00" * 160)
            self.assertEqual(core.transcribe(client, path, "gpt-4o-mini-transcribe"), "你好 Ultron")
        self.assertEqual(client.audio.transcriptions.create.call_args.kwargs["model"], "gpt-4o-mini-transcribe")

    def test_tts_disabled(self):
        with patch.object(core.subprocess, "Popen") as popen:
            self.assertTrue(core.speak("hello", voice="Tingting", enabled=False))
            popen.assert_not_called()

    def test_missing_api_key_short_circuits(self):
        with patch.object(core.sys, "platform", "darwin"), patch.dict(os.environ, {}, clear=True):
            self.assertEqual(core.main(["--text", "hello", "--no-speech"]), 2)

    def test_doctor_does_not_require_credentials(self):
        with patch.object(core.sys, "platform", "darwin"), patch.dict(os.environ, {}, clear=True):
            self.assertEqual(core.main(["--doctor"]), 0)


if __name__ == "__main__":
    unittest.main()
