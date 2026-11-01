#!/usr/bin/env python3
"""Generate ULTRON original synthetic voice audition WAVs on user's Mac.

Files remain local. Calls OpenAI Speech API and may incur API charges.
"""
import argparse
import os
import sys
from pathlib import Path

from personas import PERSONAS, SAMPLE_CN, SAMPLE_EN, synthesize, play_wav


def main():
    parser = argparse.ArgumentParser(description="Preview original ULTRON synthetic voices")
    parser.add_argument("--persona", choices=[*PERSONAS, "all"], default="all")
    parser.add_argument("--language", choices=["zh", "en"], default="zh")
    parser.add_argument("--output-dir", type=Path, default=Path("voiceos/voice-previews"))
    parser.add_argument("--play", action="store_true", help="Play generated WAVs with macOS afplay")
    parser.add_argument("--model", default="gpt-4o-mini-tts")
    parser.add_argument("--force", action="store_true", help="Regenerate a cached preview and make another paid request")
    parser.add_argument("--robotic", type=int, default=25, help="Robot effect strength, 0 to 100 (default 25)")
    parser.add_argument("--from-wav", type=Path, help="Use a previously generated 16-bit PCM WAV for zero-API-cost effect audition")
    args = parser.parse_args()
    if not 0 <= args.robotic <= 100:
        parser.error("--robotic must be 0..100")
    from robotic_fx import process_robotic
    args.output_dir.mkdir(parents=True, exist_ok=True)
    if args.from_wav is not None:
        if not args.from_wav.is_file():
            parser.error(f"Source WAV does not exist: {args.from_wav}")
        target = args.output_dir / f"{args.from_wav.stem}-robotic-{args.robotic}.wav"
        process_robotic(args.from_wav, target, strength=args.robotic)
        print(f"[VoiceOS] Offline processing (no API call), saved {target}")
        if args.play:
            play_wav(target)
        return 0
    # Previously generated WAVs may be processed/played without API credentials.
    selected = list(PERSONAS) if args.persona == "all" else [args.persona]
    cache_ready = all((args.output_dir / f"ultron-{persona}-{args.language}.wav").is_file() for persona in selected)
    if not cache_ready or args.force:
        if not os.getenv("OPENAI_API_KEY"):
            print("OPENAI_API_KEY not set for uncached voice generation.", file=sys.stderr)
            return 2
    # Reuse the safe local HTTPS proxy discovery in VoiceOS.
    client = None
    if not cache_ready or args.force:
        from core import configure_proxy
        configure_proxy()
        from openai import OpenAI
        client = OpenAI(timeout=30, max_retries=0)
    script = SAMPLE_CN if args.language == "zh" else SAMPLE_EN
    print("[VoiceOS] AI-generated voice previews. Not an imitation of any actor.")
    print("[VoiceOS] Only uncached previews call paid OpenAI TTS; API timeout 30s, zero retries.")
    for persona in selected:
        print(f"[VoiceOS] Generating {persona.upper()} ({args.language})...", flush=True)
        target = args.output_dir / f"ultron-{persona}-{args.language}.wav"
        if target.is_file() and target.stat().st_size > 100 and not args.force:
            print(f"[VoiceOS] Using cached preview (no API charge): {target}", flush=True)
        else:
            if client is None:
                from core import configure_proxy
                configure_proxy()
                from openai import OpenAI
                client = OpenAI(timeout=30, max_retries=0)
            synthesize(client, script, target, persona=persona, model=args.model)
            print(f"[VoiceOS] Saved {target}", flush=True)
        playback = target
        if args.robotic:
            playback = args.output_dir / f"ultron-{persona}-{args.language}-robotic-{args.robotic}.wav"
            process_robotic(target, playback, strength=args.robotic)
            print(f"[VoiceOS] Saved processed preview {playback}")
        if args.play:
            play_wav(playback)
    return 0


if __name__ == "__main__":
    sys.exit(main())
