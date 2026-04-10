# глобальный обработчик ошибок: логирует всё и не даёт боту упасть

import logging
import traceback

from telegram import Update
from telegram.ext import Application, ContextTypes

from services.callback_feedback import answer_callback

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

    if update.callback_query:
        await answer_callback(
            update.callback_query,
            "Сбой в боте. Нажми /start или попробуй чуть позже.",
            alert=True,
        )
        return

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
