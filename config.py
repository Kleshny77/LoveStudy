# настройки из .env; один вход для всего приложения
import os
from pathlib import Path

from dotenv import load_dotenv

# Явный путь: не зависит от cwd (systemd, cron, -m bot из другой папки).
load_dotenv(Path(__file__).resolve().parent / ".env")


def get_bot_token() -> str:
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise SystemExit(
            "Задай BOT_TOKEN в .env (скопируй .env.example в .env и вставь токен от @BotFather)."
        )
    return token


def get_database_url() -> str | None:
    return os.getenv("DATABASE_URL") or None


def get_analytics_enabled() -> bool:
    """Запись событий в таблицу analytics_events (нужен DATABASE_URL)."""
    raw = (os.getenv("ANALYTICS_ENABLED") or "1").strip().lower()
    return raw not in ("0", "false", "no", "off")


def get_gemini_api_key() -> str | None:
    """API-ключ Gemini для генерации викторин (fallback)."""
    return os.getenv("GEMINI_API_KEY") or None


def get_gemini_proxy_api_key() -> str | None:
    """API-ключ Gemini-compatible провайдера (например, artemox)."""
    return os.getenv("GEMINI_PROXY_API_KEY") or None


def get_gemini_proxy_base_url() -> str:
    """Base URL Gemini-compatible провайдера."""
    return os.getenv("GEMINI_PROXY_BASE_URL", "https://api.artemox.com/v1").rstrip("/")


def get_gemini_proxy_model() -> str:
    """Модель Gemini-compatible провайдера."""
    return os.getenv("GEMINI_PROXY_MODEL", "gemini-3.1-flash-lite-preview")


def get_deepseek_api_key() -> str | None:
    """API-ключ DeepSeek для генерации викторин. Приоритет для текстовых материалов."""
    return os.getenv("DEEPSEEK_API_KEY") or None


def get_groq_api_key() -> str | None:
    """API-ключ Groq (Llama) для генерации викторин. Используется как fallback после DeepSeek."""
    return os.getenv("GROQ_API_KEY") or None


def is_quiz_ai_configured() -> bool:
    """True, если задан хотя бы один ключ для генерации викторин."""
    return bool(
        get_gemini_proxy_api_key()
        or get_deepseek_api_key()
        or get_groq_api_key()
        or get_gemini_api_key()
    )


def get_subscription_price_stars() -> int:
    """Цена подписки LoveStudy Pro в Telegram Stars."""
    raw = os.getenv("SUBSCRIPTION_PRICE_STARS", "199").strip()
    try:
        value = int(raw)
    except ValueError:
        return 199
    return max(1, value)


def get_payment_support_contact() -> str | None:
    """Контакт для вопросов по оплате: @username, ссылка или email."""
    value = (os.getenv("PAY_SUPPORT_CONTACT") or "").strip()
    return value or None
