"""Offline tests for energy VAD and hands-free CLI wiring."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
import wave
from unittest.mock import patch, MagicMock

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("handsfree", ROOT / "handsfree.py")
hf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hf)


class TestHandsfree(unittest.TestCase):
    def setUp(self):
        self.vad = hf.MicVAD(rate=16000, block_ms=30, threshold=550,
                             speech_ms=240, end_silence_ms=750)

    def block(self, value):
        return np.full(self.vad.frames, value, dtype=np.int16).tobytes()

    def test_rms(self):
        self.assertEqual(self.vad.rms(self.block(0)), 0.0)
        self.assertAlmostEqual(self.vad.rms(self.block(1000)), 1000.0)
        self.assertFalse(self.vad.loud(self.block(400)))
        self.assertTrue(self.vad.loud(self.block(600)))

    def test_write_wav(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "sample.wav"
            hf.write_wav(path, [self.block(100), self.block(200)], rate=16000)
            with wave.open(str(path), "rb") as wav:
                self.assertEqual(wav.getnchannels(), 1)
                self.assertEqual(wav.getframerate(), 16000)
                self.assertEqual(wav.getnframes(), self.vad.frames * 2)

    def test_wav_barge_in_player_clean_exit(self):
        from contextlib import nullcontext
        with tempfile.TemporaryDirectory() as d:
            output = Path(d) / "sample.wav"
            hf.write_wav(output, [self.block(100)], rate=self.vad.rate)
            process = MagicMock()
            process.poll.return_value = 0
            process.returncode = 0
            with patch.object(hf, "_open_stream", return_value=nullcontext()), \
                 patch.object(hf.subprocess, "Popen", return_value=process) as launch:
                self.assertTrue(hf.play_wav_with_barge_in(output, vad=self.vad))
                self.assertEqual(launch.call_args.args[0], ["afplay", str(output)])

    def test_wav_barge_in_requires_source_file(self):
        with self.assertRaises(FileNotFoundError):
            hf.play_wav_with_barge_in("/missing/ultron.wav", vad=self.vad)

    def test_threshold_rejection(self):
        with self.assertRaises(ValueError):
            hf.MicVAD(rate=0)


if __name__ == "__main__":
    unittest.main()
