#!/usr/bin/env python3
"""Сводка метрик в терминале (та же БД, что у бота). Metabase не нужен.

Запуск из корня репозитория:
  ./venv/bin/python scripts/print_analytics_report.py

На сервере:
  cd ~/app && ./venv/bin/python scripts/print_analytics_report.py

Нужен DATABASE_URL в .env (как у бота).
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


def _print_title(s: str) -> None:
    print()
    print("=" * 60)
    print(s)
    print("=" * 60)


def _print_rows(rows: list, colnames: list[str]) -> None:
    if not rows:
        print("  (нет данных)")
        return
    widths = [len(c) for c in colnames]
    for row in rows:
        for i, v in enumerate(row):
            widths[i] = max(widths[i], len(str(v)))
    fmt = "  " + " | ".join(f"{{:{w}}}" for w in widths)
    print(fmt.format(*colnames))
    print("  " + "-+-".join("-" * w for w in widths))
    for row in rows:
        print(fmt.format(*(str(x) if x is not None else "" for x in row)))


async def main() -> None:
    engine = get_engine()
    if engine is None:
        print("DATABASE_URL не задан в .env — не к чему подключаться.")
        sys.exit(1)

    try:
        async with engine.connect() as conn:
            _print_title("База")
            r = (await conn.execute(text("SELECT count(*) FROM users"))).scalar_one()
            print(f"  Пользователей (users): {r}")
            r = (await conn.execute(text("SELECT count(*) FROM analytics_events"))).scalar_one()
            print(f"  Событий (analytics_events): {r}")

            _print_title("DAU — уникальные user_telegram_id по дням (последние 14 дней)")
            q = text("""
                SELECT date_trunc('day', created_at AT TIME ZONE 'UTC')::date AS day,
                       count(DISTINCT user_telegram_id) AS dau
                FROM analytics_events
                WHERE created_at >= now() - interval '14 days'
                GROUP BY 1
                ORDER BY 1 DESC
            """)
            res = await conn.execute(q)
            rows = res.fetchall()
            _print_rows(rows, ["day", "dau"])

            _print_title("События за 30 дней (имя → количество)")
            q = text("""
                SELECT event_name, count(*) AS n
                FROM analytics_events
                WHERE created_at >= now() - interval '30 days'
                GROUP BY 1
                ORDER BY n DESC
            """)
            res = await conn.execute(q)
            rows = res.fetchall()
            _print_rows(rows, ["event_name", "n"])

            _print_title("Каналы (users.acquisition_ref), топ-20")
            try:
                q = text("""
                    SELECT coalesce(acquisition_ref, '(пусто)') AS ref, count(*) AS n
                    FROM users
                    GROUP BY 1
                    ORDER BY n DESC
                    LIMIT 20
                """)
                res = await conn.execute(q)
                rows = res.fetchall()
                _print_rows(rows, ["acquisition_ref", "n"])
            except Exception as exc:
                print(f"  (пропуск — нет колонки или старая схема): {exc}")

            _print_title("Помодоро — завершённые рабочие сессии за 30 дней")
            q = text("""
                SELECT count(*) AS sessions,
                       coalesce(sum(work_minutes), 0) AS total_work_minutes
                FROM pomodoro_session_logs
                WHERE completed_at >= now() - interval '30 days'
            """)
            row = (await conn.execute(q)).one()
            print(f"  Сессий: {row[0]}, суммарно минут работы: {row[1]}")

            _print_title("Генерации тестов (quiz_generated) за 30 дней")
            q = text("""
                SELECT count(*) FROM analytics_events
                WHERE event_name = 'quiz_generated'
                  AND created_at >= now() - interval '30 days'
            """)
            n = (await conn.execute(q)).scalar_one()
            print(f"  Событий quiz_generated: {n}")

        print()
        print("Подсказка: те же запросы можно вставить в Metabase → Вопрос → SQL.")
        print()
    except Exception as exc:
        print("Ошибка:", exc)
        sys.exit(1)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
