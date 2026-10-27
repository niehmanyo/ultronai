"""Ultron Original Voice: audible electronic/robotic WAV transformation.

Offline NumPy DSP. 0 is byte-identical original. Higher values blend
an intentionally obvious ring-modulated, saturated electronic voice.
This is NOT a frequency-band vocoder, cloned voice, or actor imitation.
"""
from __future__ import annotations

import wave
from pathlib import Path

import numpy as np


def process_robotic(source: Path, target: Path, *, strength: int = 25) -> Path:
    if not 0 <= strength <= 100:
        raise ValueError("robotic strength must be 0..100")
    source, target = Path(source), Path(target)
    if source.resolve() == target.resolve():
        raise ValueError("source and target must be different paths")
    if strength == 0:
        target.write_bytes(source.read_bytes())
        return target

    with wave.open(str(source), "rb") as wav:
        channels, rate, width = wav.getnchannels(), wav.getframerate(), wav.getsampwidth()
        raw = wav.readframes(wav.getnframes())
    if channels not in (1, 2) or width != 2 or rate < 8000:
        raise ValueError("robotic filter requires 16-bit PCM mono/stereo WAV at >= 8000 Hz")
    samples = np.frombuffer(raw, dtype="<i2").astype(np.float32).reshape(-1, channels) / 32768.0
    if samples.size == 0:
        target.write_bytes(source.read_bytes())
        return target

    amount = strength / 100.0
    t = np.arange(len(samples), dtype=np.float32) / rate
    # Ring modulation produces strong metallic sidebands. Use two non-harmonic
    # carriers so the result is unmistakably synthetic instead of just echoey.
    carrier = (0.67 * np.cos(2 * np.pi * 92 * t)
               + 0.33 * np.cos(2 * np.pi * 147 * t))[:, None]
    ring_voice = samples * carrier

    # Soft harmonic drive enhances articulation in the modulated signal.
    driven = np.tanh(3.0 * ring_voice) / np.tanh(3.0)
    # Two short comb delays create synthetic resonance without long reverb.
    delayed = np.zeros_like(driven)
    for milliseconds, gain in ((7.0, 0.25), (14.5, -0.18)):
        offset = max(1, round(rate * milliseconds / 1000))
        if offset < len(driven):
            delayed[offset:] += driven[:-offset] * gain
    wet = np.tanh(1.35 * (driven + delayed)) / np.tanh(1.35)

    # Actual effect mix: the old implementation accidentally made
    # 45% strength nearly inaudible through very small multiplied gains.
    # New mapping: 25 -> 35% wet, 45 -> 56% wet, 70 -> 78% wet.
    mix = 0.12 + 0.88 * (amount ** 0.65)
    out = (1.0 - mix) * samples + mix * wet

    # Slight loudness control; avoid hard clipping and retain intelligibility.
    peak = float(np.max(np.abs(out)))
    if peak > 0.97:
        out *= 0.97 / peak
    pcm = np.clip(np.rint(out * 32768.0), -32768, 32767).astype("<i2").tobytes()
    with wave.open(str(target), "wb") as wav:
        wav.setnchannels(channels)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        wav.writeframes(pcm)
    return target
