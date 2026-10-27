#!/usr/bin/env python3
"""Ultron VoiceOS core MVP: microphone -> OpenAI STT -> DSH SDK -> macOS say.

Runs locally without a web UI. The SDK owns a separate runtime from DSH Web.
Requires explicit OPENAI_API_KEY in the process environment; never prints it.
"""
from __future__ import annotations

import argparse
import os
import select
import subprocess
import sys
import tempfile
import time
import wave
from pathlib import Path


def configure_proxy() -> None:
    """Mirror the safe loopback HTTPS proxy discovery from harness/start-local.sh."""
    if sys.platform != "darwin" or os.getenv("ULTRON_PROXY_AUTO", "1") == "0":
        return
    if any(os.getenv(k) for k in ("HTTPS_PROXY", "https_proxy", "ALL_PROXY", "all_proxy")):
        return
    try:
        result = subprocess.run(["scutil", "--proxy"], capture_output=True, text=True, timeout=3, check=True)
        data = {}
        for line in result.stdout.splitlines():
            parts = line.strip().split(" : ", 1)
            if len(parts) == 2:
                data[parts[0]] = parts[1]
        host, port = data.get("HTTPSProxy"), data.get("HTTPSPort", "")
        if data.get("HTTPSEnable") == "1" and host in ("localhost", "127.0.0.1") and port.isdecimal() and 1 <= int(port) <= 65535:
            import socket
            try:
                with socket.create_connection(("127.0.0.1", int(port)), timeout=0.8):
                    pass
            except OSError:
                print("[VoiceOS] System proxy is configured but not listening.", file=sys.stderr)
                return
            url = f"http://127.0.0.1:{port}"
            os.environ["HTTPS_PROXY"] = url
            os.environ.setdefault("HTTP_PROXY", url)
            os.environ.setdefault("NO_PROXY", "localhost,127.0.0.1,::1")
            print(f"[VoiceOS] Using local proxy at 127.0.0.1:{port}")
    except (OSError, subprocess.SubprocessError):
        return


def capture_wav(output: Path, *, samplerate: int = 16000, max_seconds: int = 45) -> None:
    try:
        import sounddevice as sd
    except ImportError as exc:
        raise RuntimeError("Install microphone dependencies: python3 -m pip install -r voiceos/requirements.txt") from exc

    frames: list[bytes] = []
    print("[VoiceOS] Recording... press Enter to stop. (Ctrl+C cancels)")
    started = time.monotonic()

    def callback(indata, frame_count, time_info, status):
        if status:
            print(f"[VoiceOS] Microphone warning: {status}", file=sys.stderr)
        frames.append(indata.tobytes())

    try:
        with sd.InputStream(samplerate=samplerate, channels=1, dtype="int16", callback=callback):
            while time.monotonic() - started < max_seconds:
                readable, _, _ = select.select([sys.stdin], [], [], 0.1)
                if readable:
                    sys.stdin.readline()
                    break
    except KeyboardInterrupt:
        raise
    except Exception as exc:
        raise RuntimeError(f"Microphone capture failed: {exc}; check macOS Microphone permission and input device") from exc

    if not frames:
        raise RuntimeError("No microphone samples recorded.")
    with wave.open(str(output), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(samplerate)
        wav.writeframes(b"".join(frames))


def transcribe(client, path: Path, model: str) -> str:
    with path.open("rb") as audio:
        result = client.audio.transcriptions.create(model=model, file=audio)
    return str(result.text).strip()


def speak(text: str, *, voice: str, enabled: bool = True) -> bool:
    """Return True if spoken completely; False if the user interrupted."""
    if not enabled or not text.strip():
        return True
    process = subprocess.Popen(["say", "-v", voice, text], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    print("[VoiceOS] Speaking. Press Enter to interrupt playback.")
    try:
        while process.poll() is None:
            readable, _, _ = select.select([sys.stdin], [], [], 0.1)
            if readable:
                sys.stdin.readline()
                process.terminate()
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
                return False
        if process.returncode:
            detail = (process.stderr.read() if process.stderr else b"").decode(errors="replace")[:200]
            raise RuntimeError(f"macOS say failed: {detail}")
        return True
    finally:
        if process.poll() is None:
            process.terminate()
            process.wait()


def run_agent(harness, prompt: str, session_id: str) -> str:
    result = harness.run(prompt, session_id=session_id)
    return str(result.final_response or "").strip()


def build_parser():
    p = argparse.ArgumentParser(description="Ultron VoiceOS terminal speech core MVP")
    p.add_argument("--model", default=os.getenv("ULTRON_VOICE_MODEL", "gpt-4.1-mini"))
    p.add_argument("--provider", default=os.getenv("ULTRON_VOICE_PROVIDER", "openai"))
    p.add_argument("--profile", default=os.getenv("ULTRON_VOICE_PROFILE", "sdk"))
    p.add_argument("--stt-model", default=os.getenv("ULTRON_STT_MODEL", "gpt-4o-mini-transcribe"))
    p.add_argument("--voice", default=os.getenv("ULTRON_MAC_VOICE", "Tingting"))
    p.add_argument("--session-id", default="ultron-voiceos-mvp")
    p.add_argument("--workspace", type=Path, default=Path(__file__).resolve().parents[1] / "ultron-workspace")
    p.add_argument("--text", help="Skip microphone/STT and send this text to DSH (integration smoke test)")
    p.add_argument("--no-speech", action="store_true", help="Disable macOS TTS playback")
    p.add_argument("--doctor", action="store_true", help="Check dependencies, without making model calls")
    return p


def doctor(args) -> int:
    print("[VoiceOS] Python:", sys.version.split()[0], "Platform:", sys.platform)
    print("[VoiceOS] OPENAI_API_KEY:", "set" if os.getenv("OPENAI_API_KEY") else "NOT SET")
    print("[VoiceOS] DSH_HOME:", os.getenv("DSH_HOME", str(Path.home() / ".ultron-dsh")))
    print("[VoiceOS] Proxy:", "configured" if os.getenv("HTTPS_PROXY") else "none")
    for name in ("openai", "sounddevice", "deepseek_harness"):
        try:
            __import__(name)
            print(f"[VoiceOS] {name}: installed")
        except (ImportError, OSError) as exc:
            print(f"[VoiceOS] {name}: unavailable ({exc})")
    if sys.platform == "darwin":
        try:
            r = subprocess.run(["say", "-v", "?"], capture_output=True, text=True, timeout=5)
            print("[VoiceOS] macOS say:", "available" if r.returncode == 0 else "not available")
        except OSError:
            print("[VoiceOS] macOS say: not available")
    print("[VoiceOS] Provider/model:", args.provider, args.model, "Profile:", args.profile)
    print("[VoiceOS] NOTE: SDK has its own runtime and does not attach to DSH Web sessions.")
    return 0


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    if sys.platform != "darwin":
        print("[VoiceOS] This MVP requires macOS for microphone and speech output.", file=sys.stderr)
        return 2
    configure_proxy()
    if args.doctor:
        return doctor(args)
    if not os.getenv("OPENAI_API_KEY"):
        print("[VoiceOS] OPENAI_API_KEY is required in the terminal environment (different from DSH Web credentials).", file=sys.stderr)
        print("[VoiceOS] Never commit or paste the key in GitHub or logs.", file=sys.stderr)
        return 2

    try:
        from deepseek_harness import DeepSeekHarness
        from openai import OpenAI
    except (ImportError, OSError) as exc:
        print(f"[VoiceOS] Missing dependency: {exc}. Install voiceos/requirements.txt", file=sys.stderr)
        return 2

    client = OpenAI(timeout=90, max_retries=1)
    home = str(Path(os.getenv("DSH_HOME") or Path.home() / ".ultron-dsh").expanduser().resolve())
    workspace = str(args.workspace.expanduser().resolve())
    if not Path(workspace).is_dir():
        print("[VoiceOS] Workspace directory does not exist.", file=sys.stderr)
        return 2

    print("[VoiceOS] Starting DSH SDK runtime; Web UI session is not shared.")
    try:
        with DeepSeekHarness(
            dsh_home=home, cwd=workspace, profile=args.profile,
            provider=args.provider, model=args.model,
        ) as harness:
            pending_text = args.text
            while True:
                if pending_text is not None:
                    user_text = pending_text
                    pending_text = None
                else:
                    command = input("\n[VoiceOS] Enter to record / q to quit: ").strip().lower()
                    if command in ("q", "quit", "exit"):
                        break
                    with tempfile.TemporaryDirectory(prefix="ultron-voice-") as tmp:
                        wav = Path(tmp) / "speech.wav"
                        capture_wav(wav)
                        print("[VoiceOS] Transcribing...")
                        user_text = transcribe(client, wav, args.stt_model)
                if not user_text:
                    print("[VoiceOS] No speech recognized.")
                    continue
                print("[You]", user_text)
                print("[VoiceOS] Agent processing...")
                reply = run_agent(harness, user_text, args.session_id)
                print("[Ultron]", reply or "(No final assistant message)")
                speak(reply, voice=args.voice, enabled=not args.no_speech)
    except KeyboardInterrupt:
        print("\n[VoiceOS] Interrupted.")
    except Exception as exc:
        # Never print credential values or full model request objects.
        print(f"[VoiceOS] Error: {type(exc).__name__}: {str(exc)[:350]}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
