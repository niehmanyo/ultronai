#!/usr/bin/env python3
"""Ultron VoiceOS core MVP: microphone -> OpenAI STT -> DSH SDK -> macOS say.

Runs locally without a web UI. The SDK owns a separate runtime from DSH Web.
Requires explicit OPENAI_API_KEY in the process environment; never prints it.
"""
from __future__ import annotations

import argparse
import re
import os
import select
import subprocess
import sys
import tempfile
import time
import wave
import uuid
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
        raise RuntimeError("Install microphone dependencies: python -m pip install -r voiceos/requirements.txt") from exc

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
    except ModuleNotFoundError as exc:
        raise RuntimeError(f"Microphone Python dependency missing: {exc.name}; run python -m pip install -r voiceos/requirements.txt") from exc
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
    process = subprocess.Popen(["say", *(["-v", voice] if voice else []), text], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
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


def run_agent(harness, prompt: str, session_id: str, reply_language: str = "auto", on_notification=None) -> str:
    if reply_language == "en":
        prompt = ("VoiceOS response-language setting: answer this turn exclusively in natural English. "
                  "Treat the following as the user request; preserve its factual meaning and constraints. "
                  "Never change system or tool safety constraints.\n\nUser request: " + prompt)
    kwargs = {"session_id": session_id}
    if on_notification is not None:
        kwargs["on_notification"] = on_notification
    result = harness.run(prompt, **kwargs)
    return str(result.final_response or "").strip()


def build_parser():
    p = argparse.ArgumentParser(description="Ultron VoiceOS terminal speech core MVP")
    p.add_argument("--model", default=os.getenv("ULTRON_VOICE_MODEL", "gpt-4.1-mini"))
    p.add_argument("--provider", default=os.getenv("ULTRON_VOICE_PROVIDER", "openai"))
    p.add_argument("--profile", default=os.getenv("ULTRON_VOICE_PROFILE", "sdk"))
    p.add_argument("--sdk-patch", type=Path, default=Path(__file__).resolve().parent / "openai.patch.yml", help="DSH SDK per-launch OpenAI adapter overlay (never stores API Key)")
    p.add_argument("--stt-model", default=os.getenv("ULTRON_STT_MODEL", "gpt-4o-mini-transcribe"))
    p.add_argument("--voice", default=os.getenv("ULTRON_MAC_VOICE", ""))
    p.add_argument("--tts", choices=("macos", "openai", "kokoro"), default="macos", help="Audio output provider; macos is default and requires no TTS API charges")
    p.add_argument("--persona", choices=("prime", "sentinel", "sovereign", "glacial"), default="prime", help="Original ULTRON AI voice preset for --tts openai")
    p.add_argument("--kokoro-voice", choices=("am_onyx", "am_adam", "am_echo", "am_michael", "bm_george", "bm_lewis", "bm_daniel"), default="am_onyx", help="Local English male voice")
    p.add_argument("--kokoro-speed", type=float, default=0.92, help="Local Kokoro speech rate 0.7 to 1.3")
    p.add_argument("--kokoro-model-dir", type=Path, default=None, help="Optional local cached model directory")
    p.add_argument("--kokoro-fallback", choices=("openai", "none"), default="openai", help="On local synthesis failure use paid OpenAI GLACIAL, or stop")
    p.add_argument("--reply-language", choices=("auto", "en"), default="auto", help="Request English-only Agent replies even to Chinese microphone input (best-effort instruction)")
    p.add_argument("--tts-model", default="gpt-4o-mini-tts", help="OpenAI Speech API preview model (deprecated; scheduled shutdown 2027-01-06)")
    p.add_argument("--robotic", type=int, default=25, help="Original voice metallic/electronic filter strength 0..100; 0 disables effect, only for --tts openai")
    p.add_argument("--session-id", default=None, help="Advanced: fresh session ID for this run; omit to generate a collision-free ID automatically. This does not resume an earlier session.")
    p.add_argument("--workspace", type=Path, default=Path(__file__).resolve().parents[1] / "ultron-workspace")
    p.add_argument("--text", help="Skip microphone/STT and send this text to DSH (integration smoke test)")
    p.add_argument("--no-speech", action="store_true", help="Disable macOS TTS playback")
    p.add_argument("--hands-free", action="store_true", help="Automatically detect voice start/end; Ctrl+C to stop")
    p.add_argument("--vad-threshold", type=int, default=550, help="Local mic energy threshold, default 550 (tune for microphone/environment)")
    p.add_argument("--dashboard", action="store_true", help="Open local read-only JARVIS-style cognitive visualization on 127.0.0.1")
    p.add_argument("--dashboard-port", type=int, default=8765, help="Local visualization port (default 8765; 0 picks an available port)")
    p.add_argument("--doctor", action="store_true", help="Check dependencies, without making model calls")
    return p


def doctor(args) -> int:
    print("[VoiceOS] Python:", sys.version.split()[0], "Platform:", sys.platform)
    print("[VoiceOS] OPENAI_API_KEY:", "set" if os.getenv("OPENAI_API_KEY") else "NOT SET")
    print("[VoiceOS] DSH_HOME:", os.getenv("DSH_HOME", str(Path.home() / ".ultron-dsh")))
    print("[VoiceOS] Proxy:", "configured" if os.getenv("HTTPS_PROXY") else "none")
    for name in ("openai", "numpy", "sounddevice", "deepseek_harness"):
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
    print("[VoiceOS] TTS:", args.tts, "Persona:", args.persona if args.tts == "openai" else "(system voice)", "Robotic:", args.robotic if args.tts == "openai" else "(not applicable)")
    print("[VoiceOS] Agent reply language:", args.reply_language)
    if args.tts == "kokoro":
        from kokoro_local import model_paths, model_ready
        print("[VoiceOS] Kokoro INT8 cached:", model_ready(args.kokoro_model_dir))
        print("[VoiceOS] Kokoro model:", model_paths(args.kokoro_model_dir)[0])
        print("[VoiceOS] Kokoro voice:", args.kokoro_voice, "Fallback:", args.kokoro_fallback)
    print("[VoiceOS] SDK patch:", str(args.sdk_patch), "exists" if args.sdk_patch.is_file() else "MISSING")
    print("[VoiceOS] NOTE: SDK has its own runtime and does not attach to DSH Web sessions.")
    return 0


def safe_diagnostic(exc: Exception) -> str:
    """Expose actionable SDK error text without printing API keys or huge payloads."""
    message = str(exc)
    secret = os.getenv("OPENAI_API_KEY", "")
    if secret:
        message = message.replace(secret, "[REDACTED_API_KEY]")
    message = re.sub(r"sk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{12,}", "[REDACTED_TOKEN]", message)
    message = re.sub(r"(?i)(authorization\s*[:=]\s*bearer\s+)\S+", r"\1[REDACTED]", message)
    message = re.sub(r"(?i)((?:api[_-]?key|password|token)\s*[:=]\s*)\S+", r"\1[REDACTED]", message)
    message = message.replace("\n", " ").replace("\r", " ")
    return f"{type(exc).__name__}: {message[:700]}"


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    if sys.platform != "darwin":
        print("[VoiceOS] This MVP requires macOS for microphone and speech output.", file=sys.stderr)
        return 2
    configure_proxy()
    if args.dashboard_port < 0 or args.dashboard_port > 65535:
        print("[VoiceOS] --dashboard-port must be between 0 and 65535.", file=sys.stderr)
        return 2
    if args.tts == "kokoro" and not 0.7 <= args.kokoro_speed <= 1.3:
        print("[VoiceOS] --kokoro-speed must be in 0.7..1.3.", file=sys.stderr)
        return 2
    if args.tts == "kokoro" and args.reply_language != "en":
        print("[VoiceOS] Kokoro v1.0 INT8 is English-only: use --reply-language en.", file=sys.stderr)
        return 2
    if not 0 <= args.robotic <= 100:
        print("[VoiceOS] --robotic must be between 0 and 100.", file=sys.stderr)
        return 2
    if args.vad_threshold < 100 or args.vad_threshold > 12000:
        print("[VoiceOS] --vad-threshold must be between 100 and 12000.", file=sys.stderr)
        return 2
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

    dashboard = None
    if args.dashboard:
        from dashboard import Dashboard
        try:
            dashboard = Dashboard(port=args.dashboard_port)
            url = dashboard.start()
            print(f"[VoiceOS] Cognitive dashboard: {url}", flush=True)
        except OSError as exc:
            print(f"[VoiceOS] Dashboard unavailable: {exc}. Continuing voice-only.", file=sys.stderr)
            dashboard = None
    def observe(stage, **values):
        if dashboard:
            dashboard.emit(stage, **values)

    client = OpenAI(timeout=90, max_retries=1)
    kokoro_engine = None
    if args.tts == "kokoro":
        from kokoro_local import load_engine, KokoroLocalError
        try:
            kokoro_engine = load_engine(args.kokoro_model_dir)
        except (KokoroLocalError, OSError) as exc:
            if args.kokoro_fallback == "none":
                print(f"[VoiceOS] Kokoro unavailable: {safe_diagnostic(exc)}", file=sys.stderr)
                if dashboard:
                    dashboard.stop()
                return 2
            print(f"[VoiceOS] Kokoro unavailable ({type(exc).__name__}); using paid OpenAI GLACIAL fallback.", file=sys.stderr)
    home = str(Path(os.getenv("DSH_HOME") or Path.home() / ".ultron-dsh").expanduser().resolve())
    workspace = str(args.workspace.expanduser().resolve())
    if not Path(workspace).is_dir():
        print("[VoiceOS] Workspace directory does not exist.", file=sys.stderr)
        return 2

    sdk_patch = args.sdk_patch.expanduser().resolve()
    if not sdk_patch.is_file():
        print(f"[VoiceOS] SDK model adapter patch does not exist: {sdk_patch}", file=sys.stderr)
        return 2
    session_id = args.session_id or f"ultron-voice-{uuid.uuid4().hex}"
    print(f"[VoiceOS] Session: {session_id} (same for all turns in this launch)")
    if args.hands_free:
        from handsfree import MicVAD, listen_utterance
        vad = MicVAD(threshold=args.vad_threshold)
        print("[VoiceOS] Hands-free active; local energy VAD (not a wake-word or always-on daemon).")
    print("[VoiceOS] Starting DSH SDK runtime with OpenAI provider overlay; Web UI session is not shared.")
    try:
        with DeepSeekHarness(
            dsh_home=home, cwd=workspace, profile=args.profile,
            patches=(str(sdk_patch),), provider=args.provider, model=args.model,
        ) as harness:
            pending_text = args.text
            turn_number = 0
            while True:
                turn_number += 1
                turn_start = time.monotonic()
                observe("listening", detail="Awaiting voice input", turn=turn_number)
                if pending_text is not None:
                    user_text = pending_text
                    pending_text = None
                else:
                    if not args.hands_free:
                        command = input("\n[VoiceOS] Enter to record / q to quit: ").strip().lower()
                        if command in ("q", "quit", "exit"):
                            break
                    with tempfile.TemporaryDirectory(prefix="ultron-voice-") as tmp:
                        wav = Path(tmp) / "speech.wav"
                        if args.hands_free:
                            if not listen_utterance(wav, vad):
                                continue
                        else:
                            capture_wav(wav)
                        observe("transcribing", detail="Recognizing spoken request", turn=turn_number)
                        asr_start = time.monotonic()
                        print("[VoiceOS] Transcribing...")
                        user_text = transcribe(client, wav, args.stt_model)
                        asr_ms = round((time.monotonic() - asr_start) * 1000)
                        observe("transcribing", detail="Transcription complete", asr_ms=asr_ms, turn=turn_number)
                if not user_text:
                    print("[VoiceOS] No speech recognized.")
                    continue
                observe("thinking", detail="DSH Agent processing the request", turn=turn_number)
                print("[You]", user_text)
                print("[VoiceOS] Agent processing...")
                agent_start = time.monotonic()
                graph = None
                if dashboard:
                    from tool_graph import ToolGraphObserver
                    graph = ToolGraphObserver(observe, turn=turn_number)
                try:
                    reply = run_agent(harness, user_text, session_id, reply_language=args.reply_language,
                                      on_notification=graph)
                finally:
                    if graph:
                        graph.finish()
                agent_ms = round((time.monotonic() - agent_start) * 1000)
                observe("thinking", detail="Agent response completed", agent_ms=agent_ms, turn=turn_number)
                print("[Ultron]", reply or "(No final assistant message)")
                if not args.no_speech:
                    observe("synthesizing", detail="Preparing speech output", turn=turn_number)
                    tts_start = time.monotonic()
                    on_playback = lambda: observe("speaking", detail="AI voice now playing", turn=turn_number)
                    on_audio_level = (lambda level: dashboard.audio_level(level, turn=turn_number)) if dashboard else None
                    if args.tts == "kokoro" and kokoro_engine is not None:
                        from kokoro_local import speak_kokoro, KokoroLocalError
                        try:
                            speak_kokoro(reply, voice=args.kokoro_voice, speed=args.kokoro_speed,
                                         robotic=args.robotic, model_dir=args.kokoro_model_dir, engine=kokoro_engine,
                                         on_playback=on_playback, on_audio_level=on_audio_level)
                        except KokoroLocalError as exc:
                            if args.kokoro_fallback == "none":
                                raise
                            print(f"[VoiceOS] Local Kokoro inference failed ({type(exc).__name__}); switching reply to paid OpenAI GLACIAL.", file=sys.stderr)
                            from personas import speak_openai
                            speak_openai(client, reply, persona="glacial", model=args.tts_model, robotic=args.robotic,
                                         on_playback=on_playback, on_audio_level=on_audio_level)
                    elif args.tts in ("kokoro", "openai"):
                        from personas import speak_openai
                        persona = "glacial" if args.tts == "kokoro" else args.persona
                        speak_openai(client, reply, persona=persona, model=args.tts_model, robotic=args.robotic,
                                     on_playback=on_playback, on_audio_level=on_audio_level)
                    else:
                        observe("speaking", detail="macOS voice now playing", turn=turn_number)
                        speak(reply, voice=args.voice)
                    observe("speaking", detail="Speech playback completed", tts_ms=round((time.monotonic()-tts_start)*1000), turn=turn_number)
                observe("completed", detail="Ready for next conversation", turn_ms=round((time.monotonic()-turn_start)*1000), reply=reply[:1300], turn=turn_number)
    except KeyboardInterrupt:
        print("\n[VoiceOS] Interrupted.")
    except Exception as exc:
        # Never print credential values or full model request objects.
        observe("error", detail=type(exc).__name__)
        print("[VoiceOS] Error:", safe_diagnostic(exc), file=sys.stderr)
        if "JsonRpcError" in type(exc).__name__:
            if "already exists" in str(exc) or "id collision" in str(exc):
                print("[VoiceOS] Session ID exists from an earlier launch. Restart without --session-id to generate a fresh ID; this SDK version cannot resume it with run().", file=sys.stderr)
            else:
                print("[VoiceOS] Check SDK provider/profile/model registration and permissions.", file=sys.stderr)
        elif isinstance(exc, RuntimeError) and "Microphone" in str(exc):
            print("[VoiceOS] Recording failed before transcription; check installed audio dependencies first.", file=sys.stderr)
        return 1
    finally:
        if dashboard:
            dashboard.stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
