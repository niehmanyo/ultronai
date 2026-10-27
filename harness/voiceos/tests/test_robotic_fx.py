"""Offline DSP tests: no paid speech generation calls."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
import wave
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("robotic_fx", ROOT / "robotic_fx.py")
fx = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fx)


class TestRoboticAudio(unittest.TestCase):
    def make_wav(self, path, channels=1):
        rate = 24000
        t = np.arange(rate // 3, dtype=np.float32) / rate
        base = (np.sin(2 * np.pi * 180 * t) * 9500).astype("<i2")
        audio = base if channels == 1 else np.column_stack([base, base]).ravel()
        with wave.open(str(path), "wb") as out:
            out.setnchannels(channels)
            out.setsampwidth(2)
            out.setframerate(rate)
            out.writeframes(audio.tobytes())

    def test_zero_bypass_is_byte_identical(self):
        with tempfile.TemporaryDirectory() as d:
            src, dst = Path(d) / "orig.wav", Path(d) / "off.wav"
            self.make_wav(src)
            fx.process_robotic(src, dst, strength=0)
            self.assertEqual(src.read_bytes(), dst.read_bytes())

    def test_processed_audio_is_valid_and_different(self):
        with tempfile.TemporaryDirectory() as d:
            for channels in (1, 2):
                src, dst = Path(d) / "orig.wav", Path(d) / "fx.wav"
                self.make_wav(src, channels)
                fx.process_robotic(src, dst, strength=70)
                self.assertNotEqual(src.read_bytes(), dst.read_bytes())
                with wave.open(str(dst), "rb") as result:
                    self.assertEqual(result.getnchannels(), channels)
                    self.assertEqual(result.getsampwidth(), 2)
                    self.assertEqual(result.getframerate(), 24000)
                    self.assertEqual(result.getnframes(), 8000)

    def test_invalid_parameters(self):
        with tempfile.TemporaryDirectory() as d:
            src, dst = Path(d) / "orig.wav", Path(d) / "fx.wav"
            self.make_wav(src)
            for strength in (-1, 101):
                with self.assertRaises(ValueError):
                    fx.process_robotic(src, dst, strength=strength)
            with self.assertRaises(ValueError):
                fx.process_robotic(src, src, strength=10)


if __name__ == "__main__":
    unittest.main()
