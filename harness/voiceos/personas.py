"""Ultron Original Voice V0.1: selectable synthetic TTS personas.

Preview voices use OpenAI's built-in TTS voice + delivery instructions.
They are NOT persisted custom voice IDs, actor clones or unique voiceprints.
All generated speech must be disclosed as AI-generated to listeners.
"""
from __future__ import annotations

import subprocess
import tempfile
import wave
from pathlib import Path

PERSONAS = {
    "prime": {
        "voice": "onyx",
        "instructions": (
            "Speak as an original, mature artificial intelligence interface. "
            "Male-presenting low register with warm resonance, controlled pacing, "
            "precise diction and calm authority. Sound natural and understated, "
            "not like any movie character or recognizable celebrity. "
            "Speak Mandarin fluently when the input is Chinese; speak English "
            "naturally when the input is English. Slightly slower than conversational "
            "pace, with small meaningful pauses. Avoid melodrama and robotic monotone."
        ),
    },
    "sentinel": {
        "voice": "cedar",
        "instructions": (
            "An original sophisticated adult AI assistant voice: smooth, composed, "
            "measured and subtly warm. Clear articulation, elegant cadence and "
            "thoughtful pauses. Natural fluent Mandarin for Chinese, natural "
            "English for English. Understated intelligence; never imitate a named "
            "actor or fictional character."
        ),
    },
    "sovereign": {
        "voice": "onyx",
        "instructions": (
            "Speak as an original, austere machine intelligence. Deep, dark, firm, "
            "emotionally distant adult male-presenting voice. No smile in the voice, "
            "no warmth, reassurance, friendliness, or customer-service intonation. "
            "Short, sharp declarative phrasing; deliberate controlled tempo; "
            "flat sentence endings and metallic precision. Sound cold and formidable "
            "without shouting or theatrical villainy. Maintain crisp intelligibility "
            "in English or Mandarin. Never mimic any actor or copyrighted character."
        ),
    },
    "glacial": {
        "voice": "onyx",
        "instructions": (
            "Original cold synthetic-command voice, masculine and low-pitched. "
            "Extremely restrained emotion: grave, severe, impersonal and unyielding. "
            "Speak English with crisp clipped consonants, long steady vowels, "
            "measured pauses and a slight metallic machine-like regularity. "
            "Every sentence lands with a decisive falling cadence. "
            "No soft reassurance, no cheerfulness, no conversational warmth, "
            "no smiling or sing-song melody. Pronounce each word with authority; "
            "do not growl, shout, distort or imitate any identifiable actor."
        ),
    },
}

SAMPLE_CN = (
    "奥创已上线。所有系统运行正常。"
    "我已准备就绪，可以协助分析问题、执行任务，并报告进展。"
)
SAMPLE_EN = (
    "Ultron online. Core systems synchronized. "
    "Threat assessment complete. Authorization confirmed. "
    "State your objective. I will execute with precision."
)


def available_personas():
    return tuple(PERSONAS)


def synthesize(client, text: str, target: Path, *, persona="prime",
               model="gpt-4o-mini-tts"):
    """Synthesize a WAV using OpenAI Speech API; requires network and API billing."""
    if persona not in PERSONAS:
        raise ValueError(f"Unknown persona {persona!r}. Choose: {', '.join(PERSONAS)}")
    if not text.strip():
        raise ValueError("Cannot synthesize empty text")
    if len(text) > 4000:
        raise ValueError("TTS input too long; split the reply into shorter chunks")
    p = PERSONAS[persona]
    print(f"[VoiceOS] TTS request: model={model}, persona={persona}, characters={len(text)}", flush=True)
    response = client.audio.speech.create(
        model=model,
        voice=p["voice"],
        input=text,
        instructions=p["instructions"],
        response_format="wav",
    )
    print("[VoiceOS] TTS response received; saving WAV...", flush=True)
    response.stream_to_file(target)
    if not target.is_file() or target.stat().st_size < 100:
        raise RuntimeError("TTS returned an empty/invalid WAV file")
    with wave.open(str(target), "rb") as audio:
        if audio.getnframes() < 100 or audio.getframerate() < 8000:
            raise RuntimeError("TTS WAV has no playable audio frames")
        seconds = audio.getnframes() / audio.getframerate()
    print(f"[VoiceOS] TTS WAV ready: {seconds:.1f}s, {target.stat().st_size} bytes", flush=True)
    return target


def play_wav(path: Path):
    """Block while playing WAV via macOS built-in player."""
    print(f"[VoiceOS] Playing audio: {path}", flush=True)
    subprocess.run(["afplay", str(path)], check=True, timeout=120)
    print("[VoiceOS] Audio playback finished.", flush=True)


def speak_openai(client, text: str, *, persona="prime", model="gpt-4o-mini-tts", robotic=25):
    if not text.strip():
        return True
    print("[VoiceOS] Preparing AI speech synthesis...", flush=True)
    with tempfile.TemporaryDirectory(prefix="ultron-tts-") as temp:
        output = Path(temp) / "reply.wav"
        synthesize(client, text, output, persona=persona, model=model)
        playback = output
        if robotic:
            from robotic_fx import process_robotic
            playback = process_robotic(output, Path(temp) / "robotic.wav", strength=robotic)
        print(f"[VoiceOS] Speaking with ULTRON {persona.upper()} (AI-generated voice, robotic={robotic}).")
        print("[VoiceOS] Audio effects ready; starting player.", flush=True)
        play_wav(playback)
    return True
