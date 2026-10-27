"""Subtle robotic timbre for Ultron's original synthetic TTS.

Offline postprocessing for PCM16 WAV. Not voice cloning, no external DSP tools.
Strength 0 = bit-identical bypass; larger strengths add mild metallic modulation
and short electronic resonance. Preserve intelligibility with dry-signal blend.
"""
from __future__ import annotations

import wave
from pathlib import Path
import numpy as np


def process_robotic(source: Path, target: Path, *, strength: int = 25) -> Path:
    if not 0 <= strength <= 100:
        raise ValueError("robotic strength must be 0..100")
    source = Path(source)
    target = Path(target)
    if source.resolve() == target.resolve():
        raise ValueError("source and target must be different paths")
    if strength == 0:
        target.write_bytes(source.read_bytes())
        return target

    with wave.open(str(source), "rb") as wav:
        channels = wav.getnchannels()
        rate = wav.getframerate()
        width = wav.getsampwidth()
        frames = wav.getnframes()
        raw = wav.readframes(frames)
    if width != 2 or channels not in (1, 2):
        raise ValueError("robotic filter requires mono/stereo 16-bit PCM WAV")
    if rate < 8000:
        raise ValueError("sample rate too low")
    samples = np.frombuffer(raw, dtype="<i2").astype(np.float32).reshape(-1, channels)
    if samples.size == 0:
        target.write_bytes(source.read_bytes())
        return target

    amount = strength / 100.0
    # A gentle sideband is perceived as electronic without disguising speech.
    t = np.arange(len(samples), dtype=np.float32) / rate
    ring = np.sin(2 * np.pi * 83.0 * t)[:, None]
    modulated = samples * (1 - 0.16 * amount + 0.16 * amount * ring)
    # Two very short, low-level resonances. Keep a high dry-to-wet ratio.
    delay_a = max(1, round(rate * 0.009))
    delay_b = max(1, round(rate * 0.017))
    resonance = np.zeros_like(samples)
    resonance[delay_a:] += samples[:-delay_a] * (0.17 * amount)
    resonance[delay_b:] -= samples[:-delay_b] * (0.10 * amount)
    wet = modulated + resonance
    out = samples * (1 - 0.48 * amount) + wet * (0.48 * amount)
    # Avoid hard clipping of previously near-full-scale voice.
    peak = float(np.max(np.abs(out)))
    if peak > 32000:
        out *= 32000.0 / peak
    pcm = np.clip(np.rint(out), -32768, 32767).astype("<i2").tobytes()
    with wave.open(str(target), "wb") as result:
        result.setnchannels(channels)
        result.setsampwidth(2)
        result.setframerate(rate)
        result.writeframes(pcm)
    return target
