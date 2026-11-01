"""Unit tests for privacy-preserving 3D speech amplitude envelope."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
import wave

import numpy as np

MODULE = Path(__file__).resolve().parents[1] / "audio_meter.py"
spec = importlib.util.spec_from_file_location("voice_audio_meter", MODULE)
meter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(meter)


class TestAudioMeter(unittest.TestCase):
    def write_wav(self, path, samples, channels=1, rate=24000):
        with wave.open(str(path), "wb") as wav:
            wav.setnchannels(channels)
            wav.setsampwidth(2)
            wav.setframerate(rate)
            wav.writeframes(np.asarray(samples, dtype="<i2").tobytes())

    def test_silence_returns_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "silent.wav"
            self.write_wav(path, np.zeros(2400, dtype=np.int16))
            self.assertTrue(all(v == 0 for v in meter.amplitude_envelope(path)))

    def test_follows_actual_loudness_in_mono(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "speech.wav"
            samples = np.concatenate([
                np.zeros(1200, dtype=np.int16),
                np.full(1200, 2000, dtype=np.int16),
                np.full(1200, 12000, dtype=np.int16)])
            self.write_wav(path, samples)
            result = meter.amplitude_envelope(path)
            self.assertEqual(len(result), 3)
            self.assertEqual(result[0], 0)
            self.assertLess(result[1], result[2])
            self.assertLessEqual(result[2], 1.0)

    def test_stereo_and_invalid_window(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "stereo.wav"
            frames = np.tile([2000, -2000], (2400, 1))
            self.write_wav(path, frames.ravel(), channels=2)
            self.assertEqual(len(meter.amplitude_envelope(path)), 2)
            with self.assertRaises(ValueError):
                meter.amplitude_envelope(path, window_ms=1)


if __name__ == "__main__":
    unittest.main()
