"""Offline Kokoro INT8 voice adapter tests; no model download or paid API."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch
import wave

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("kokoro_local", ROOT / "kokoro_local.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class TestLocalKokoro(unittest.TestCase):
    def test_split_preserves_content(self):
        source = ("Ultron online. This is a long validation sentence. " * 12).strip()
        parts = mod.split_utterances(source, limit=100)
        self.assertTrue(all(len(p) <= 100 for p in parts))
        self.assertEqual(" ".join(parts), source)

    def test_invalid_configuration(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertFalse(mod.model_ready(d))
            with self.assertRaises(mod.KokoroLocalError):
                mod.load_engine(d)
        engine = MagicMock()
        with self.assertRaises(ValueError):
            mod.synthesize_kokoro("Hello", Path("unused.wav"), voice="no_voice", engine=engine)
        with self.assertRaises(ValueError):
            mod.synthesize_kokoro("Hello", Path("unused.wav"), speed=2, engine=engine)

    def test_synthesize_writes_pcm16_wav_and_chunks(self):
        fake = MagicMock()
        fake.create.side_effect = lambda text, **kwargs: (np.full(2400, .25, dtype=np.float32), 24000)
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "voice.wav"
            output = mod.synthesize_kokoro("Ultron online. Systems active.", target, engine=fake)
            self.assertEqual(target, output)
            with wave.open(str(output), "rb") as wav:
                self.assertEqual(wav.getsampwidth(), 2)
                self.assertEqual(wav.getnchannels(), 1)
                self.assertEqual(wav.getframerate(), 24000)
                self.assertEqual(wav.getnframes(), 2400)
            self.assertEqual(fake.create.call_args.kwargs["voice"], "am_onyx")
            self.assertEqual(fake.create.call_args.kwargs["lang"], "en-us")

    def test_synthesis_failure_does_not_leave_output(self):
        fake = MagicMock()
        fake.create.side_effect = RuntimeError("broken inference")
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "error.wav"
            with self.assertRaises(mod.KokoroLocalError):
                mod.synthesize_kokoro("Test", target, engine=fake)
            self.assertFalse(target.exists())

    def test_existing_audio_can_drive_3d_pipeline(self):
        fake = MagicMock()
        fake.create.return_value = (np.full(4800, .4, dtype=np.float32), 24000)
        with tempfile.TemporaryDirectory() as directory:
            output = mod.synthesize_kokoro("Systems online.", Path(directory)/"audio.wav", engine=fake)
            with wave.open(str(output), "rb") as wav:
                self.assertEqual(wav.getnframes(), 4800)
            # The existing audio_meter expects a regular PCM16 WAV; no extra adapter required.
            self.assertGreater(output.stat().st_size, 100)


if __name__ == "__main__":
    unittest.main()
