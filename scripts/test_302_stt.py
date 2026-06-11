#!/usr/bin/env python3
"""Probe 302.AI STT API variants; prints status codes only (no secrets)."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import httpx

BASE = os.getenv("AI302_BASE_URL", "https://api.302.ai").rstrip("/")
KEY = os.getenv("AI302_API_KEY", "").strip().strip('"').strip("'")
MODELS = ("whisper-v3-turbo", "whisper-v3", "whisper-1", "whisper-large-v3")
AUTH_MODES = (
    ("Bearer", lambda k: {"Authorization": f"Bearer {k}", "Accept": "application/json"}),
    ("Raw", lambda k: {"Authorization": k, "Accept": "application/json"}),
    ("302-api-key", lambda k: {"302-api-key": k, "Accept": "application/json"}),
    ("api-key", lambda k: {"api-key": k, "Accept": "application/json"}),
)


def sample_mp3() -> Path:
    path = Path("/tmp/test-302-stt.mp3")
    if path.exists() and path.stat().st_size > 1000:
        return path
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:duration=2",
            "-ar",
            "16000",
            "-ac",
            "1",
            "-q:a",
            "4",
            str(path),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return path


def try_request(name: str, url: str, headers: dict, mp3: Path) -> None:
    data = {"model": "whisper-v3-turbo"}
    files = {"file": (mp3.name, mp3.read_bytes(), "audio/mpeg")}
    try:
        r = httpx.post(url, headers=headers, data=data, files=files, timeout=60)
    except Exception as exc:
        print(f"FAIL {name}: transport {exc}")
        return
    body = r.text.strip().replace("\n", " ")[:180]
    print(f"{r.status_code} {name}: {body}")


def main() -> int:
    if not KEY or KEY == "replace-me":
        print("AI302_API_KEY missing")
        return 1

    mp3 = sample_mp3()
    print(f"sample={mp3.name} bytes={mp3.stat().st_size} key_prefix={KEY[:8]}...")

    url = f"{BASE}/v1/audio/transcriptions"
    for auth_name, auth_fn in AUTH_MODES:
        headers = auth_fn(KEY)
        try_request(f"auth={auth_name} data+files", url, headers, mp3)

    headers = AUTH_MODES[0][1](KEY)
    multipart = [
        ("file", (mp3.name, mp3.read_bytes(), "audio/mpeg")),
        ("model", (None, "whisper-v3-turbo")),
    ]
    try:
        r = httpx.post(url, headers=headers, files=multipart, timeout=60)
        print(f"{r.status_code} multipart-only: {r.text.strip()[:180]}")
    except Exception as exc:
        print(f"FAIL multipart-only: {exc}")

    for model in MODELS:
        multipart = [
            ("file", (mp3.name, mp3.read_bytes(), "audio/mpeg")),
            ("model", (None, model)),
        ]
        try:
            r = httpx.post(url, headers=headers, files=multipart, timeout=60)
            print(f"{r.status_code} model={model}: {r.text.strip()[:120]}")
        except Exception as exc:
            print(f"FAIL model={model}: {exc}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
