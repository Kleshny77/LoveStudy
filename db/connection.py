# движок SQLAlchemy и инициализация схемы.
# Каждая миграция выполняется в ОТДЕЛЬНОЙ транзакции — иначе после первой
# ошибки PostgreSQL отменяет всю транзакцию и остальные ADD COLUMN не применяются.

import logging
import os
import re
import ssl
from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from config import get_database_url
from db.models import Base

logger = logging.getLogger(__name__)

_engine: Optional[AsyncEngine] = None
_ROOT_CRT = os.path.expanduser("~/.postgresql/root.crt")

# Каждый элемент — отдельная транзакция при старте.
# ADD COLUMN IF NOT EXISTS — идемпотентно.
# DROP NOT NULL — идемпотентно в PostgreSQL (уже nullable → no-op, успех).
_MIGRATIONS = [
    "ALTER TABLE materials ADD COLUMN IF NOT EXISTS file_unique_id  VARCHAR(512)",
    "ALTER TABLE materials ADD COLUMN IF NOT EXISTS file_size       BIGINT",
    "ALTER TABLE materials ADD COLUMN IF NOT EXISTS mime_type       VARCHAR(128)",
    "ALTER TABLE materials ADD COLUMN IF NOT EXISTS url             TEXT",
    "ALTER TABLE materials ALTER COLUMN telegram_file_id  DROP NOT NULL",
    "ALTER TABLE materials ALTER COLUMN original_filename DROP NOT NULL",
    # streak-поля в users
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS streak_days        INTEGER NOT NULL DEFAULT 0",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS last_activity_date DATE",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS quiz_correct_answers INTEGER NOT NULL DEFAULT 0",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS quiz_wrong_answers   INTEGER NOT NULL DEFAULT 0",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS quiz_generations_today INTEGER NOT NULL DEFAULT 0",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS quiz_generations_date DATE",
    # friendships
    """CREATE TABLE IF NOT EXISTS friendships (
        id         BIGSERIAL PRIMARY KEY,
        user1_id   BIGINT NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
        user2_id   BIGINT NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        CONSTRAINT uq_friendship UNIQUE (user1_id, user2_id)
    )""",
    # pomodoro_settings создаётся через create_all, но на случай если таблица
    # уже существует без нужных колонок — добавляем колонки вручную:
    """CREATE TABLE IF NOT EXISTS pomodoro_settings (
        user_telegram_id  BIGINT PRIMARY KEY REFERENCES users(telegram_id) ON DELETE CASCADE,
        work_minutes      INTEGER NOT NULL DEFAULT 25,
        break_minutes     INTEGER NOT NULL DEFAULT 5,
        sound_enabled     BOOLEAN NOT NULL DEFAULT TRUE,
        reminder_enabled  BOOLEAN NOT NULL DEFAULT TRUE,
        auto_break        BOOLEAN NOT NULL DEFAULT TRUE,
        sessions_today    INTEGER NOT NULL DEFAULT 0,
        last_session_date DATE
    )""",
    """CREATE TABLE IF NOT EXISTS deadlines (
        id               BIGSERIAL PRIMARY KEY,
        user_telegram_id BIGINT NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
        subject_id       BIGINT REFERENCES subjects(id) ON DELETE SET NULL,
        title            VARCHAR(255) NOT NULL,
        status           VARCHAR(32) NOT NULL DEFAULT 'open',
        due_at           TIMESTAMPTZ NOT NULL,
        reminder_offset_minutes INTEGER,
        reminder_sent_at  TIMESTAMPTZ,
        completed_at     TIMESTAMPTZ,
        created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )""",
    "ALTER TABLE deadlines ADD COLUMN IF NOT EXISTS reminder_offset_minutes INTEGER",
    "ALTER TABLE deadlines ADD COLUMN IF NOT EXISTS reminder_sent_at TIMESTAMPTZ",
    "ALTER TABLE materials ADD COLUMN IF NOT EXISTS quiz_correct_answers INTEGER NOT NULL DEFAULT 0",
    "ALTER TABLE materials ADD COLUMN IF NOT EXISTS quiz_wrong_answers   INTEGER NOT NULL DEFAULT 0",
    "ALTER TABLE materials ADD COLUMN IF NOT EXISTS learned_at TIMESTAMPTZ",
    """CREATE TABLE IF NOT EXISTS deadline_settings (
        user_telegram_id       BIGINT PRIMARY KEY REFERENCES users(telegram_id) ON DELETE CASCADE,
        reminders_enabled      BOOLEAN NOT NULL DEFAULT TRUE,
        daily_digest_enabled   BOOLEAN NOT NULL DEFAULT FALSE,
        daily_digest_time      VARCHAR(5) NOT NULL DEFAULT '20:00',
        last_daily_digest_date DATE
    )""",
    """CREATE TABLE IF NOT EXISTS pomodoro_session_logs (
        id               BIGSERIAL PRIMARY KEY,
        user_telegram_id BIGINT NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
        work_minutes     INTEGER NOT NULL DEFAULT 25,
        completed_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )""",
    """CREATE TABLE IF NOT EXISTS telegram_ux_settings (
        user_telegram_id     BIGINT PRIMARY KEY REFERENCES users(telegram_id) ON DELETE CASCADE,
        study_chat_id        BIGINT,
        study_chat_title     VARCHAR(255),
        study_chat_username  VARCHAR(255),
        focus_buddy_id       BIGINT,
        focus_buddy_name     VARCHAR(255),
        focus_buddy_username VARCHAR(255),
        focus_buddy_enabled  BOOLEAN NOT NULL DEFAULT FALSE
    )""",
]


def _normalize_url(raw: str) -> str:
    """Конвертирует URL в формат для asyncpg и убирает sslmode из query-строки
    (asyncpg не понимает sslmode как query-параметр; SSL передаём через connect_args)."""
    url = raw
    # убираем sslmode=... из query string
    url = re.sub(r"[?&]sslmode=[^&]*", "", url)
    url = re.sub(r"\?$", "", url)          # убираем висячий ?
    # приводим к asyncpg-драйверу
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgresql://") and "+asyncpg" not in url:
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


def _make_ssl_context() -> Optional[ssl.SSLContext]:
    """SSL-контекст для Yandex Cloud (или любого sslmode=require).
    Если сертификат скачан — верифицируем сервер. Иначе — require без верификации."""
    if os.path.isfile(_ROOT_CRT):
        ctx = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        ctx.load_verify_locations(_ROOT_CRT)
        return ctx
    # нет сертификата, но SSL всё равно нужен (Yandex Cloud требует TLS)
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def _needs_ssl(raw_url: str) -> bool:
    return "sslmode=" in raw_url or "yandexcloud" in raw_url


def get_engine() -> Optional[AsyncEngine]:
    global _engine
    raw_url = get_database_url()
    if not raw_url:
        return None
    if _engine is None:
        url = _normalize_url(raw_url)
        echo = os.getenv("DB_ECHO", "").lower() in ("1", "true")
        connect_args: dict = {}
        if _needs_ssl(raw_url):
            connect_args["ssl"] = _make_ssl_context()
        _engine = create_async_engine(url, echo=echo, connect_args=connect_args)
        logger.debug("Engine создан: %s", url.split("@")[-1])  # не логируем пароль
    return _engine


async def init_db() -> None:
    engine = get_engine()
    if engine is None:
        return

    # 1. Создаём таблицы если их нет — отдельная транзакция
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("create_all выполнен.")

    # 2. Каждая миграция — своя транзакция.
    #    Если колонка уже есть — PostgreSQL вернёт ошибку, мы её проглотим.
    #    Если колонки нет — она будет добавлена.
    applied = 0
    for stmt in _MIGRATIONS:
        try:
            async with engine.begin() as conn:
                await conn.execute(text(stmt))
            applied += 1
            logger.debug("Миграция применена: %s", stmt[:70])
        except Exception as exc:
            logger.debug("Миграция пропущена (уже применена?): %.70s — %s", stmt, exc)

    if applied:
        logger.info("Применено миграций: %d/%d", applied, len(_MIGRATIONS))
