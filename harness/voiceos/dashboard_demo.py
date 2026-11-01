#!/usr/bin/env python3
"""Preview the VoiceOS UI without a microphone, SDK or paid API request.

All activity in this command is synthetic and visibly labeled DEMO.
Do not use it as a latency or correctness benchmark.
"""
import argparse
import time
import webbrowser
from dashboard import Dashboard


def main():
    parser = argparse.ArgumentParser(description="VoiceOS dashboard visual demo (synthetic events)")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    if not 0 <= args.port <= 65535:
        parser.error("--port must be 0..65535")
    dash = Dashboard(args.port)
    try:
        url = dash.start()
        print(f"[DEMO ONLY] Cognitive Cortex at {url}", flush=True)
        webbrowser.open(url)
        for number in range(1, 1000000):
            phases = [
                ("listening", "DEMO · Awaiting voice", {}, 1.5),
                ("transcribing", "DEMO · Speech recognition", {}, .8),
                ("thinking", "DEMO · Agent processing", {"asr_ms": 620}, 2),
                ("synthesizing", "DEMO · Generating synthetic audio", {"agent_ms": 1820}, 1.1),
                ("speaking", "DEMO · Playing audio", {}, 2.4),
                ("completed", "DEMO · Task finished", {"tts_ms": 900, "turn_ms": 4500,
                    "reply": "[DEMO — NOT A REAL AGENT ANSWER] All systems operational."}, 1.3),
            ]
            for stage, detail, metrics, duration in phases:
                dash.emit(stage, detail=detail, turn=number, **metrics)
                time.sleep(duration)
    except KeyboardInterrupt:
        print("\n[DEMO] Exiting.")
    finally:
        dash.stop()


if __name__ == "__main__":
    main()
