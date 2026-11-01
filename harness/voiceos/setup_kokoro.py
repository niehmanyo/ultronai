#!/usr/bin/env python3
"""Explicit, one-time Kokoro v1.0 INT8 model and voice asset installer.

Downloads from the author's versioned GitHub release, never from an inferred
host or through a VoiceOS conversation. Assets are user-local, not committed.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import tempfile
from urllib.request import urlopen

from kokoro_local import DEFAULT_MODEL_DIR, MODEL_NAME, VOICES_NAME, model_paths, model_ready

BASE = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/"
FILES = {MODEL_NAME: 80_000_000, VOICES_NAME: 10_000_000}


def download_asset(name, destination: Path, *, min_bytes, force=False):
    if name not in FILES:
        raise ValueError("Unexpected asset name")
    if destination.is_file() and destination.stat().st_size >= min_bytes and not force:
        print(f"[Kokoro] Cached: {destination}")
        return destination
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(prefix=".download-", dir=destination.parent, delete=False) as tmp:
        temporary = Path(tmp.name)
    try:
        print(f"[Kokoro] Downloading {name} from versioned upstream release...", flush=True)
        with urlopen(BASE + name, timeout=60) as source, temporary.open("wb") as file:
            length = source.headers.get("Content-Length")
            if length and int(length) > 250_000_000:
                raise RuntimeError("Unexpectedly large model download")
            shutil.copyfileobj(source, file, length=1024*1024)
        if temporary.stat().st_size < min_bytes:
            raise RuntimeError(f"Downloaded {name} is too small to be a valid model/voice file")
        temporary.replace(destination)
        print(f"[Kokoro] Saved {destination} ({destination.stat().st_size/1e6:.1f} MB)")
        return destination
    finally:
        temporary.unlink(missing_ok=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Install local Kokoro v1.0 INT8 (one-time download)")
    parser.add_argument("--model-dir", type=Path, default=DEFAULT_MODEL_DIR)
    parser.add_argument("--force", action="store_true", help="Redownload files and overwrite local cache")
    args = parser.parse_args(argv)
    root = args.model_dir.expanduser()
    model_path, voices_path = model_paths(root)
    try:
        download_asset(MODEL_NAME, model_path, min_bytes=FILES[MODEL_NAME], force=args.force)
        download_asset(VOICES_NAME, voices_path, min_bytes=FILES[VOICES_NAME], force=args.force)
    except Exception as exc:
        print(f"[Kokoro] Installation failed ({type(exc).__name__}): {exc}")
        return 1
    if not model_ready(root):
        print("[Kokoro] Installation incomplete.")
        return 1
    print("[Kokoro] Local assets ready. All subsequent synthesis runs offline.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
