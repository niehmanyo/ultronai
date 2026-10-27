"""Ultron Original Voice V0.1: selectable synthetic TTS personas.

Preview voices use OpenAI's built-in TTS voice + delivery instructions.
They are NOT persisted custom voice IDs, actor clones or unique voiceprints.
All generated speech must be disclosed as AI-generated to listeners.
"""
from __future__ import annotations

import subprocess
import tempfile
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
            "An original futuristic AI command voice, with deep resonant tone, "
            "deliberate rhythm and restrained intensity. Natural speech, "
            "very subtle metallic texture conveyed only through precise delivery; "
            "no theatrical villain performance. Fluent Mandarin and English; "
            "respond in the language of the text. Do not impersonate any individual."
        ),
    },
}

SAMPLE_CN = (
    "奥创已上线。所有系统运行正常。"
    "我已准备就绪，可以协助分析问题、执行任务，并报告进展。"
)
SAMPLE_EN = (
    "Ultron online. All systems operational. "
    "Ready to assist with analysis, execution, and clear reporting."
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
    response = client.audio.speech.create(
        model=model,
        voice=p["voice"],
        input=text,
        instructions=p["instructions"],
        response_format="wav",
    )
    response.stream_to_file(target)
    return target


def play_wav(path: Path):
    """Block while playing WAV via macOS built-in player."""
    subprocess.run(["afplay", str(path)], check=True)


def speak_openai(client, text: str, *, persona="prime", model="gpt-4o-mini-tts", robotic=25):
    if not text.strip():
        return True
    with tempfile.TemporaryDirectory(prefix="ultron-tts-") as temp:
        output = Path(temp) / "reply.wav"
        synthesize(client, text, output, persona=persona, model=model)
        playback = output
        if robotic:
            from robotic_fx import process_robotic
            playback = process_robotic(output, Path(temp) / "robotic.wav", strength=robotic)
        print(f"[VoiceOS] Speaking with ULTRON {persona.upper()} (AI-generated voice, robotic={robotic}).")
        play_wav(playback)
    return True
