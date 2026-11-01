"""Hands-free microphone utterance capture for VoiceOS.

Local energy-based VAD: no separate ML model or cloud VAD.
Microphone turns are captured sequentially, after prior speech playback.
"""
from __future__ import annotations

from collections import deque
import queue
import time
import wave

import numpy as np


class MicVAD:
    def __init__(self, *, rate=16000, block_ms=30, threshold=550,
                 speech_ms=240, end_silence_ms=750, max_seconds=35):
        if rate <= 0 or block_ms <= 0:
            raise ValueError("sample rate and block duration must be positive")
        self.rate = rate
        self.block_ms = block_ms
        self.frames = int(rate * block_ms / 1000)
        self.threshold = threshold
        self.min_speech_blocks = max(1, round(speech_ms / block_ms))
        self.max_silence_blocks = max(1, round(end_silence_ms / block_ms))
        self.max_blocks = max(1, round(max_seconds * 1000 / block_ms))

    def rms(self, raw: bytes) -> float:
        audio = np.frombuffer(raw, dtype=np.int16)
        if audio.size == 0:
            return 0.0
        return float(np.sqrt(np.mean(audio.astype(np.float32) ** 2)))

    def loud(self, raw: bytes) -> bool:
        return self.rms(raw) >= self.threshold


def write_wav(path, blocks, *, rate):
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        wav.writeframes(b"".join(blocks))


def _open_stream(vad, samples):
    import sounddevice as sd
    def callback(indata, frames, timing, status):
        # Keep PortAudio's callback nonblocking: discard if consumer falls behind.
        try:
            samples.put_nowait(bytes(indata))
        except queue.Full:
            pass
    return sd.RawInputStream(
        samplerate=vad.rate, channels=1, dtype="int16",
        blocksize=vad.frames, callback=callback,
    )


def listen_utterance(path, vad: MicVAD, *, idle_timeout=60.0) -> bool:
    """Listen for voice then trailing silence. Returns False if no voice detected.

    Requires terminal microphone permission. A local RMS threshold is intentionally
    simple and may need tuning for quiet voices / noisy rooms.
    """
    samples = queue.Queue(maxsize=200)
    before = deque(maxlen=max(1, round(300 / vad.block_ms)))
    speech = []
    consecutive = 0
    silence = 0
    active = False
    started = time.monotonic()
    last_hint = started
    peak_rms = 0.0
    print(f"[VoiceOS] Listening automatically (RMS threshold={vad.threshold}; Ctrl+C to quit)...", flush=True)
    with _open_stream(vad, samples):
        while True:
            if not active and time.monotonic() - started > idle_timeout:
                print("[VoiceOS] No speech detected; listening timed out.")
                return False
            try:
                block = samples.get(timeout=0.5)
            except queue.Empty:
                continue
            rms = vad.rms(block)
            voiced = rms >= vad.threshold
            if not active:
                peak_rms = max(peak_rms, rms)
                now = time.monotonic()
                if now - last_hint >= 8:
                    print(f"[VoiceOS] Waiting for speech: peak RMS={peak_rms:.0f}, threshold={vad.threshold}. Try --vad-threshold 300 if your mic is quiet.", flush=True)
                    peak_rms = 0.0
                    last_hint = now
                before.append(block)
                consecutive = consecutive + 1 if voiced else 0
                if consecutive >= vad.min_speech_blocks:
                    active = True
                    speech.extend(before)
                    before.clear()
                    print("[VoiceOS] Speech detected; listening until you pause...")
            else:
                speech.append(block)
                silence = 0 if voiced else silence + 1
                if silence >= vad.max_silence_blocks or len(speech) >= vad.max_blocks:
                    break
    if not speech:
        return False
    write_wav(path, speech, rate=vad.rate)
    return True

