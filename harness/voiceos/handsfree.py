"""Hands-free microphone utterance capture and playback interruption for VoiceOS.

Local energy-based VAD: no separate ML model or cloud VAD. Avoid loud speakers
for barge-in; use headphones to reduce echo. Audio is never logged to disk.
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
    print("[VoiceOS] Listening automatically... (Ctrl+C to quit)")
    with _open_stream(vad, samples):
        while True:
            if not active and time.monotonic() - started > idle_timeout:
                print("[VoiceOS] No speech detected; listening timed out.")
                return False
            try:
                block = samples.get(timeout=0.5)
            except queue.Empty:
                continue
            voiced = vad.loud(block)
            if not active:
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


def play_with_barge_in(text: str, *, voice="", vad: MicVAD,
                       min_play_seconds=0.7) -> bool:
    """Speak with experimental voice interruption. False means interrupted.

    Detection may falsely trigger on loud speaker output. Use headphones.
    Audio during interruption is not captured as a full user utterance;
    user will be prompted to speak again.
    """
    import subprocess
    if not text.strip():
        return True
    args = ["say"]
    if voice:
        args += ["-v", voice]
    process = subprocess.Popen(args + [text], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    samples = queue.Queue(maxsize=100)
    consecutive = 0
    started = time.monotonic()
    print("[VoiceOS] Speaking (voice cut-in experimental; say something to interrupt).")
    try:
        try:
            with _open_stream(vad, samples):
                while process.poll() is None:
                    try:
                        block = samples.get(timeout=0.1)
                    except queue.Empty:
                        continue
                    if time.monotonic() - started < min_play_seconds:
                        continue
                    # Higher threshold and sustained voice are used while TTS plays.
                    if vad.rms(block) >= vad.threshold * 2.8:
                        consecutive += 1
                    else:
                        consecutive = 0
                    if consecutive >= max(1, round(450 / vad.block_ms)):
                        process.terminate()
                        try:
                            process.wait(timeout=2)
                        except subprocess.TimeoutExpired:
                            process.kill()
                            process.wait()
                        print("[VoiceOS] Playback interrupted; please say your next request after Listening appears.")
                        return False
        except Exception as exc:
            print(f"[VoiceOS] Barge-in monitor unavailable ({type(exc).__name__}); waiting for speech playback to finish.")
            process.wait()
        if process.returncode:
            raise RuntimeError("macOS speech playback failed")
        return True
    finally:
        if process.poll() is None:
            process.terminate()
            process.wait()
