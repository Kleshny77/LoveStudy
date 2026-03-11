# глобальный обработчик ошибок: логирует всё и не даёт боту упасть

import logging
import traceback

from telegram import Update
from telegram.ext import Application, ContextTypes

logger = logging.getLogger(__name__)

_USER_ERROR_MSG = (
    "Что-то пошло не так 😕 Попробуй ещё раз или напиши /start."
)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Необработанное исключение при обработке обновления:", exc_info=context.error)

    tb = "".join(traceback.format_exception(type(context.error), context.error, context.error.__traceback__))
    logger.debug("Полный traceback:\n%s", tb)

    if not isinstance(update, Update):
        return

    # Если ожидает ответа на callback — сразу закрываем «загрузку» кнопки
    if update.callback_query:
        try:
            await update.callback_query.answer()
        except Exception:
            pass

    # Отправляем пользователю понятное сообщение
    try:
        if update.effective_chat:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=_USER_ERROR_MSG,
            )
    except Exception:
        pass


def register(app: Application) -> None:
    app.add_error_handler(error_handler)
