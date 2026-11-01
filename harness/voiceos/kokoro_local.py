"""Kokoro v1.0 INT8 local English TTS provider for Ultron VoiceOS.

Uses the thewh1teagle/kokoro-onnx v1.0 INT8 model and matching voices-v1.0.bin.
Pure local inference after explicit setup; never automatically downloads at runtime.
No API key, hidden thought, or audio samples are sent to the visualization.
"""
from __future__ import annotations

import re
import tempfile
import time
import wave
from pathlib import Path
from threading import Lock

import numpy as np

DEFAULT_MODEL_DIR = Path.home() / "Library" / "Caches" / "UltronVoiceOS" / "kokoro-v1.0"
MODEL_NAME = "kokoro-v1.0.int8.onnx"
VOICES_NAME = "voices-v1.0.bin"
MALE_VOICES = ("am_onyx", "am_adam", "am_echo", "am_michael", "bm_george", "bm_lewis", "bm_daniel")
_INSTANCES = {}
_LOCK = Lock()


class KokoroLocalError(RuntimeError):
    """A local model, dependency or synthesis failure."""


def model_paths(directory=None):
    root = Path(directory).expanduser() if directory else DEFAULT_MODEL_DIR
    return root / MODEL_NAME, root / VOICES_NAME


def model_ready(directory=None):
    model, voices = model_paths(directory)
    # Sanity checks prevent a tiny HTML error response from being loaded as ONNX.
    return model.is_file() and model.stat().st_size > 40_000_000 and (
        voices.is_file() and voices.stat().st_size > 1_000_000)


def load_engine(directory=None):
    model, voices = model_paths(directory)
    if not model_ready(directory):
        raise KokoroLocalError(
            f"Kokoro INT8 model missing or incomplete in {model.parent}. "
            "Run: python voiceos/setup_kokoro.py")
    key = (str(model.resolve()), str(voices.resolve()))
    with _LOCK:
        if key not in _INSTANCES:
            try:
                from kokoro_onnx import Kokoro
            except ImportError as exc:
                raise KokoroLocalError(
                    "Install Kokoro dependencies: python -m pip install -r voiceos/requirements-kokoro.txt"
                ) from exc
            print("[VoiceOS] Loading local Kokoro INT8 model once...", flush=True)
            start = time.monotonic()
            try:
                _INSTANCES[key] = Kokoro(str(model), str(voices))
            except Exception as exc:
                raise KokoroLocalError(f"Could not load local Kokoro INT8 model: {type(exc).__name__}") from exc
            print(f"[VoiceOS] Local Kokoro INT8 ready in {time.monotonic()-start:.2f}s", flush=True)
        return _INSTANCES[key]


def split_utterances(text: str, limit: int = 220):
    """Split on punctuation/spaces, preserving all text in original order."""
    text = text.strip()
    if not text:
        return []
    if limit < 50:
        raise ValueError("limit must be >= 50")
    result = []
    while text:
        if len(text) <= limit:
            result.append(text)
            break
        section = text[:limit]
        cut = max((section.rfind(ch) + 1 for ch in ".!?;:\n" if section.rfind(ch) >= 0), default=0)
        if cut < limit // 3:
            cut = section.rfind(" ") + 1
        if cut < limit // 3:
            cut = limit
        result.append(text[:cut].strip())
        text = text[cut:].lstrip()
    return [part for part in result if part]


def synthesize_kokoro(text: str, target: Path, *, voice="am_onyx", speed=0.92,
                      model_dir=None, engine=None):
    """Generate fully local 24kHz PCM16 mono WAV from Kokoro; no HTTP requests."""
    if not text.strip():
        raise ValueError("Cannot synthesize empty text")
    if voice not in MALE_VOICES:
        raise ValueError(f"Unsupported Kokoro English male voice: {voice}")
    if not 0.7 <= speed <= 1.3:
        raise ValueError("Kokoro speed must be between 0.7 and 1.3")
    if len(text) > 12000:
        raise ValueError("Kokoro input too long (maximum 12000 characters)")
    engine = engine if engine is not None else load_engine(model_dir)
    chunks = split_utterances(text)
    output = []
    sample_rate = None
    started = time.monotonic()
    for chunk in chunks:
        try:
            audio, rate = engine.create(chunk, voice=voice, speed=speed, lang="en-us")
        except Exception as exc:
            raise KokoroLocalError(f"Kokoro inference failed: {type(exc).__name__}") from exc
        if not isinstance(rate, int) or rate < 8000:
            raise KokoroLocalError("Kokoro returned an invalid sample rate")
        samples = np.asarray(audio, dtype=np.float32).reshape(-1)
        if not len(samples) or not np.isfinite(samples).all():
            raise KokoroLocalError("Kokoro returned invalid audio samples")
        if sample_rate is not None and sample_rate != rate:
            raise KokoroLocalError("Kokoro generated mismatched sample rates")
        sample_rate = rate
        output.append(samples)
    if not output:
        raise KokoroLocalError("No Kokoro audio generated")
    all_audio = np.concatenate(output)
    pcm = (np.clip(all_audio, -1, 1) * 32767).astype("<i2").tobytes()
    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    # Prevent corrupt partial WAVs if inference/write fails.
    with tempfile.NamedTemporaryFile(dir=target.parent, prefix=".kokoro-", suffix=".wav", delete=False) as tmp:
        temp_path = Path(tmp.name)
    try:
        with wave.open(str(temp_path), "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(sample_rate)
            wav.writeframes(pcm)
        temp_path.replace(target)
    finally:
        temp_path.unlink(missing_ok=True)
    print(f"[VoiceOS] Kokoro INT8 synthesized {len(all_audio)/sample_rate:.1f}s locally in {time.monotonic()-started:.2f}s", flush=True)
    return target


def speak_kokoro(text: str, *, voice="am_onyx", speed=0.92, robotic=55,
                 model_dir=None, on_playback=None, on_audio_level=None, engine=None):
    if not text.strip():
        return True
    from personas import play_wav
    with tempfile.TemporaryDirectory(prefix="ultron-kokoro-") as folder:
        original = Path(folder) / "original.wav"
        synthesize_kokoro(text, original, voice=voice, speed=speed,
                          model_dir=model_dir, engine=engine)
        playback = original
        if robotic:
            from robotic_fx import process_robotic
            playback = process_robotic(original, Path(folder) / "robotic.wav", strength=robotic)
        print(f"[VoiceOS] Speaking with local Kokoro INT8 ({voice}, robotic={robotic}).", flush=True)
        play_wav(playback, on_start=on_playback, on_audio_level=on_audio_level)
    return True
