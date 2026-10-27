"""Offline checks for ULTRON original TTS presets; no paid API requests."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
import wave
from unittest.mock import MagicMock

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("personas", ROOT / "personas.py")
personas = importlib.util.module_from_spec(spec)
spec.loader.exec_module(personas)


class TestPersonas(unittest.TestCase):
    def test_four_voice_styles_are_distinct(self):
        self.assertEqual(set(personas.PERSONAS), {"prime", "sentinel", "sovereign", "glacial"})
        self.assertIn("No soft reassurance", personas.PERSONAS["glacial"]["instructions"])
        self.assertIn("No smile", personas.PERSONAS["sovereign"]["instructions"])
        self.assertIn("Threat assessment", personas.SAMPLE_EN)
        self.assertNotEqual(personas.PERSONAS["prime"]["instructions"],
                            personas.PERSONAS["sovereign"]["instructions"])
        for name, preset in personas.PERSONAS.items():
            self.assertTrue(preset["voice"])
            self.assertGreater(len(preset["instructions"]), 80)

    def test_synthesize_calls_speech_api(self):
        client = MagicMock()
        client.with_options.return_value = client
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "voice.wav"
            def write_stub_wav(destination):
                with wave.open(str(destination), "wb") as output:
                    output.setnchannels(1)
                    output.setsampwidth(2)
                    output.setframerate(24000)
                    output.writeframes(b"\x00\x00" * 240)
            client.audio.speech.create.return_value.stream_to_file.side_effect = write_stub_wav
            personas.synthesize(client, "奥创已上线", path, persona="prime")
            call = client.audio.speech.create.call_args.kwargs
            self.assertEqual(call["voice"], "onyx")
            self.assertEqual(call["response_format"], "wav")
            self.assertEqual(call["input"], "奥创已上线")
            self.assertIn("Mandarin", call["instructions"])
            client.audio.speech.create.return_value.stream_to_file.assert_called_once_with(path)
            client.with_options.assert_called_once_with(timeout=30.0, max_retries=0)

    def test_rejects_unknown_persona(self):
        with self.assertRaises(ValueError):
            personas.synthesize(MagicMock(), "Hello", Path("x.wav"), persona="unknown")

    def test_rejects_empty_text(self):
        with self.assertRaises(ValueError):
            personas.synthesize(MagicMock(), "", Path("x.wav"))


if __name__ == "__main__":
    unittest.main()
