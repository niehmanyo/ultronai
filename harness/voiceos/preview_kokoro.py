#!/usr/bin/env python3
"""Preview local Kokoro INT8 English voices without an Agent/API/TTS charge."""
from __future__ import annotations

import argparse
from pathlib import Path
import time

from kokoro_local import DEFAULT_MODEL_DIR, MALE_VOICES, load_engine, synthesize_kokoro


SAMPLE = ("Ultron online. Core systems synchronized. "
          "Threat assessment complete. State your objective.")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Offline Kokoro INT8 male voice preview")
    parser.add_argument("--voice", choices=MALE_VOICES, default="am_onyx")
    parser.add_argument("--speed", type=float, default=0.92)
    parser.add_argument("--robotic", type=int, default=55)
    parser.add_argument("--text", default=SAMPLE)
    parser.add_argument("--model-dir", type=Path, default=DEFAULT_MODEL_DIR)
    parser.add_argument("--output-dir", type=Path, default=Path("voiceos/voice-previews"))
    parser.add_argument("--no-play", action="store_true")
    args = parser.parse_args(argv)
    if not 0 <= args.robotic <= 100:
        parser.error("--robotic must be 0..100")
    if not 0.7 <= args.speed <= 1.3:
        parser.error("--speed must be 0.7..1.3")
    from personas import play_wav
    args.output_dir.mkdir(parents=True, exist_ok=True)
    original = args.output_dir / f"kokoro-{args.voice}-en.wav"
    processed = args.output_dir / f"kokoro-{args.voice}-en-robotic-{args.robotic}.wav"
    # Real generation is local, but don't trigger it on already cached preview.
    if not original.is_file() or original.stat().st_size < 100:
        engine = load_engine(args.model_dir)
        start = time.monotonic()
        synthesize_kokoro(args.text, original, voice=args.voice, speed=args.speed, engine=engine)
        print(f"[VoiceOS] Kokoro local synthesis: {time.monotonic()-start:.2f}s")
    else:
        print(f"[VoiceOS] Reusing local preview {original}; remove it to regenerate.")
    output = original
    if args.robotic:
        from robotic_fx import process_robotic
        output = process_robotic(original, processed, strength=args.robotic)
    print(f"[VoiceOS] Preview: {output} (no TTS API call)")
    if not args.no_play:
        play_wav(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
