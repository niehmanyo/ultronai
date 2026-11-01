"""PCM16 WAV speech amplitude envelope for the visual-only neural core.

No raw speech samples or audio files are delivered to the browser. Only
normalized amplitude values, at most 20 per second, are published as SSE.
"""
from __future__ import annotations

from pathlib import Path
import wave
import numpy as np


def amplitude_envelope(path: Path, *, window_ms: int = 50) -> list[float]:
    if window_ms < 20 or window_ms > 200:
        raise ValueError("window_ms must be 20..200")
    with wave.open(str(path), "rb") as wav:
        rate, width, channels = wav.getframerate(), wav.getsampwidth(), wav.getnchannels()
        if width != 2 or channels not in (1, 2):
            raise ValueError("amplitude meter requires mono/stereo 16-bit PCM WAV")
        samples = np.frombuffer(wav.readframes(wav.getnframes()), dtype="<i2")
    if len(samples) == 0:
        return []
    mono = samples.astype(np.float32).reshape(-1, channels).mean(axis=1) / 32768.0
    size = max(1, round(rate * window_ms / 1000))
    # 50-ms block RMS, padded only at the end to prevent reshape errors.
    pad = (-len(mono)) % size
    if pad:
        mono = np.pad(mono, (0, pad))
    blocks = mono.reshape(-1, size)
    levels = np.sqrt(np.mean(blocks * blocks, axis=1))
    # Soft normalization avoids extreme fluctuations; silence remains zero.
    reference = max(float(np.percentile(levels, 90)), 0.018)
    result = np.minimum(1.0, levels / (reference * 1.20)) ** 0.72
    return [round(float(value), 3) for value in result]
