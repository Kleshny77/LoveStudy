# Application factory: собираем бота, инициализируем БД, регистрируем хендлеры

import logging

from telegram.ext import Application

from config import get_bot_token
from db.connection import get_engine, init_db
from db.repositories import get_session_factory
from handlers import register_handlers
from handlers.deadlines import setup_deadline_jobs
from handlers.telegram_setup import configure_telegram_ui

logger = logging.getLogger(__name__)


async def _on_startup(app: Application) -> None:
    # Инициализируем схему БД (создаём таблицы, если их нет)
    try:
        await init_db()
        logger.info("БД инициализирована успешно.")
    except Exception as exc:
        logger.warning("БД недоступна при старте (%s). Бот работает без сохранения данных.", exc)

    # Кладём фабрику сессий в bot_data — все хендлеры берут её оттуда
    # (None, если DATABASE_URL не задан)
    factory = get_session_factory()
    app.bot_data["session_factory"] = factory
    if factory:
        logger.info("session_factory зарегистрирована в bot_data.")
    else:
        logger.warning("DATABASE_URL не задан. Функции сохранения данных отключены.")

    try:
        await configure_telegram_ui(app)
        logger.info("Команды и menu button Telegram настроены.")
    except Exception:
        logger.exception("Не удалось настроить Telegram menu/commands")

    setup_deadline_jobs(app)


async def _on_shutdown(app: Application) -> None:
    engine = get_engine()
    if engine:
        await engine.dispose()
        logger.info("Соединения с БД закрыты.")


def create_app() -> Application:
    token = get_bot_token()
    app = (
        Application.builder()
        .token(token)
        .post_init(_on_startup)
        .post_shutdown(_on_shutdown)
        .build()
    )
    register_handlers(app)
    return app


def run_polling() -> None:
    app = create_app()
    logger.info("Бот LoveStudy запущен (polling). Остановка: Ctrl+C")
    app.run_polling(
        allowed_updates=["message", "callback_query", "poll_answer"],
        # drop_pending_updates=False (по умолчанию) — нужно для debounce /start
    )
