#!/usr/bin/env python3
"""Проверка таблицы analytics_events на сервере или локально. Запуск из корня репозитория:
   ./venv/bin/python scripts/check_analytics_events.py
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
from sqlalchemy import text

load_dotenv(ROOT / ".env")

from db.connection import get_engine  # noqa: E402


async def main() -> None:
    engine = get_engine()
    if engine is None:
        print("DATABASE_URL не задан — события не пишутся.")
        return
    try:
        async with engine.connect() as conn:
            n = (await conn.execute(text("SELECT count(*) FROM analytics_events"))).scalar_one()
        print(f"OK: analytics_events — {n} строк.")
    except Exception as exc:
        print("Ошибка:", exc)
        print("Подсказка: перезапусти бота (init_db создаст таблицу).")
        sys.exit(1)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
