#!/usr/bin/env python3
"""Один тестовый запрос к GEMINI_PROXY (OpenAI-style /chat/completions).

Запуск из корня репозитория:
  python3 scripts/test_gemini_proxy.py

На сервере (если код в ~/app):
  cd ~/app && python3 scripts/test_gemini_proxy.py --env-file ~/app/.env
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path


def _load_env(path: Path) -> None:
    """Подставляет GEMINI_PROXY_* в os.environ (без python-dotenv)."""
    import os
    import re

    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        m = re.match(r"^(GEMINI_PROXY_(?:API_KEY|BASE_URL|MODEL))=(.*)$", line)
        if not m:
            continue
        k, v = m.group(1), m.group(2).strip()
        if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
            v = v[1:-1]
        os.environ[k] = v


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description="Проверка GEMINI_PROXY_* через /chat/completions")
    parser.add_argument(
        "--env-file",
        type=Path,
        default=root / ".env",
        help="Путь к .env (по умолчанию: .env в корне репозитория)",
    )
    args = parser.parse_args()

    if not args.env_file.is_file():
        print(f"Нет файла: {args.env_file}", file=sys.stderr)
        return 1

    _load_env(args.env_file)

    import os

    key = os.getenv("GEMINI_PROXY_API_KEY")
    base = (os.getenv("GEMINI_PROXY_BASE_URL") or "").rstrip("/")
    model = os.getenv("GEMINI_PROXY_MODEL")

    if not key or not base or not model:
        print(
            "Нужны GEMINI_PROXY_API_KEY, GEMINI_PROXY_BASE_URL, GEMINI_PROXY_MODEL в .env",
            file=sys.stderr,
        )
        return 1

    url = f"{base}/chat/completions"
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "Reply with exactly: OK"}],
        "max_tokens": 16,
    }
    print(f"POST {url}")
    print(f"model={model!r}")
    data_bytes = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data_bytes,
        method="POST",
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            print(f"HTTP {resp.status}")
            data = json.loads(raw)
            msg = (data.get("choices") or [{}])[0].get("message", {}).get("content", "")
            print("content:", repr(msg[:500]))
            return 0
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace") if e.fp else ""
        print(f"HTTP {e.code}: {raw[:2000]}", file=sys.stderr)
        return 1
    except OSError as e:
        print(e, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
