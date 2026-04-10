# Единый ответ на inline-кнопку: один вызов query.answer(), понятные тексты, без падений.

from __future__ import annotations

import logging

from telegram.error import BadRequest

logger = logging.getLogger(__name__)

# Telegram ограничивает длину текста ответа на callback (~200 символов).
_MAX_CB_LEN = 190

MSG_NO_DATABASE = (
    "Сейчас не удаётся связаться с сервером. Попробуй через минуту или нажми /start."
)

MSG_QUIZ_AI_UNAVAILABLE = (
    "Тесты по материалам сейчас недоступны (сервис вопросов не настроен). Загляни позже 🙏"
)

MSG_QUIZ_LIMIT_SHORT = "На сегодня лимит генерации тестов исчерпан — загляни завтра ✨"


def clip_callback_text(text: str, max_len: int = _MAX_CB_LEN) -> str:
    t = text.strip()
    if len(t) <= max_len:
        return t
    return t[: max_len - 1] + "…"


async def answer_callback(query, text: str | None = None, *, alert: bool = False) -> None:
    """Безопасно отвечает на callback_query (игнорирует «уже ответили» и пр.)."""
    if query is None:
        return
    try:
        if text:
            await query.answer(clip_callback_text(text), show_alert=alert)
        else:
            await query.answer()
    except BadRequest as e:
        logger.debug("callback answer skipped: %s", e)
