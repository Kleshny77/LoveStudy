# /start — главный экран.
# Поддерживает deep link /start invite_<user_id> для системы друзей.
# Если бот был оффлайн и накопилась куча /start — отвечаем ровно один раз:
# каждый новый /start отменяет предыдущий отложенный ответ (debounce).

import asyncio
import logging

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes

from db.repositories import add_friend, get_or_create_user, reset_user_streak
from services.friends import (
    get_new_friend_keyboard,
    get_new_friend_text,
)
from services.analytics import EV_MAIN_MENU_SHOWN, schedule_track
from services.main_menu import get_main_menu_keyboard, get_main_menu_text

logger = logging.getLogger(__name__)

_START_DELAY = 0.7  # секунд — окно дедупликации при burst-спаме

# Хранит отложенную задачу отправки для каждого chat_id
_pending: dict[int, asyncio.Task] = {}


async def _process_invite(context: ContextTypes.DEFAULT_TYPE, inviter_id: int, new_user_id: int) -> None:
    """Создаёт дружбу и уведомляет инвайтера."""
    if inviter_id == new_user_id:
        return
    async with context.bot_data["session_factory"]() as session:
        added = await add_friend(session, inviter_id, new_user_id)
        if not added:
            return
        # Получаем данные нового пользователя для уведомления
        from sqlalchemy import select
        from db.models import User
        result = await session.execute(select(User).where(User.telegram_id == new_user_id))
        new_user = result.scalar_one_or_none()

    if new_user is None:
        return

    name    = new_user.first_name or new_user.username or "Новый друг"
    uname   = new_user.username
    try:
        await context.bot.send_message(
            chat_id=inviter_id,
            text=get_new_friend_text(name, uname),
            reply_markup=get_new_friend_keyboard(),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        logger.exception("Не удалось уведомить инвайтера %s", inviter_id)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_chat or not update.effective_user:
        return

    chat_id = update.effective_chat.id
    uid     = update.effective_user.id
    name    = update.effective_user.first_name
    username = update.effective_user.username

    # ── Обработка deep link (/start invite_<inviter_id>) ──
    args = context.args or []
    inviter_id: int | None = None
    if args and args[0].startswith("invite_"):
        try:
            inviter_id = int(args[0][len("invite_"):])
        except ValueError:
            pass

    # ── Стрик будет считаться по тестам, а не по /start.
    #    Сбрасываем старое legacy-значение daily-visit, если оно осталось в БД.
    factory = context.bot_data.get("session_factory")
    if factory:
        try:
            async with factory() as session:
                await get_or_create_user(
                    session,
                    telegram_id=uid,
                    username=username,
                    first_name=name,
                )
                await reset_user_streak(session, uid)
        except Exception:
            logger.exception("Ошибка при get_or_create_user/reset_streak (uid=%s)", uid)

    # Отменяем предыдущую ожидающую задачу для этого чата
    old_task = _pending.pop(chat_id, None)
    if old_task is not None:
        old_task.cancel()

    async def _send() -> None:
        try:
            await asyncio.sleep(_START_DELAY)

            # Обрабатываем invite (создаём дружбу, уведомляем инвайтера)
            if inviter_id is not None:
                await _process_invite(context, inviter_id, uid)

            # Главное меню
            schedule_track(
                context,
                uid,
                EV_MAIN_MENU_SHOWN,
                {"from_invite": inviter_id is not None},
            )
            await context.bot.send_message(
                chat_id=chat_id,
                text=get_main_menu_text(name),
                reply_markup=get_main_menu_keyboard(),
                parse_mode="HTML",
            )
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Ошибка при отправке стартового сообщения (chat_id=%s)", chat_id)
        finally:
            _pending.pop(chat_id, None)

    task = asyncio.create_task(_send())
    _pending[chat_id] = task


def register(app: Application) -> None:
    app.add_handler(CommandHandler("start", start))
