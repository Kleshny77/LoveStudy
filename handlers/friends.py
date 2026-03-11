# Флоу «Друзья и рейтинг»: хаб, рейтинг, список друзей,
# профиль, поиск друга по @username, приглашение.

import logging
import re

from telegram import Update
from telegram.constants import ParseMode
from telegram.error import BadRequest
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    ContextTypes,
)

from constants import (
    CB_FRI_ACHIEV, CB_FRI_INVITE, CB_FRI_LIST, CB_FRI_RATING,
    CB_FRIENDS, CB_NAV_MAIN,
)
from handlers.achievements import open_from_friends as open_achievements
from db.repositories import (
    get_friends,
    get_friends_rating,
)
from services.friends import (
    get_friends_list_keyboard,
    get_friends_list_text,
    get_hub_no_friends_text,
    get_invite_keyboard,
    get_invite_text,
    get_rating_keyboard,
    get_rating_text,
)

logger = logging.getLogger(__name__)

_HTML = ParseMode.HTML


# ──────────────────────────────────────────────
# Вспомогательные
# ──────────────────────────────────────────────

async def _safe_edit(query, text: str, keyboard, parse_mode=_HTML) -> None:
    try:
        await query.edit_message_text(
            text,
            reply_markup=keyboard,
            parse_mode=parse_mode,
            disable_web_page_preview=True,
        )
    except BadRequest:
        await query.message.reply_text(
            text,
            reply_markup=keyboard,
            parse_mode=parse_mode,
            disable_web_page_preview=True,
        )


# ──────────────────────────────────────────────
# Хаб «Друзья и рейтинг»
# ──────────────────────────────────────────────

async def open_friends_hub(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    uid = update.effective_user.id
    async with context.bot_data["session_factory"]() as session:
        friends = await get_friends(session, uid)
        rating  = await get_friends_rating(session, uid)

    if not friends:
        bot_name   = (await context.bot.get_me()).username
        invite_link = f"t.me/{bot_name}?start=invite_{uid}"
        text = get_hub_no_friends_text()
        kbd = get_invite_keyboard(invite_link, back_cb=CB_NAV_MAIN)
    else:
        text = get_rating_text(rating, uid)
        kbd = get_rating_keyboard()

    await _safe_edit(query, text, kbd)


# ──────────────────────────────────────────────
# Рейтинг
# ──────────────────────────────────────────────

async def open_rating(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    uid = update.effective_user.id
    async with context.bot_data["session_factory"]() as session:
        ranking = await get_friends_rating(session, uid)

    text = get_rating_text(ranking, uid)
    await _safe_edit(query, text, get_rating_keyboard())


# ──────────────────────────────────────────────
# Список друзей
# ──────────────────────────────────────────────

async def open_friends_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    uid = update.effective_user.id
    async with context.bot_data["session_factory"]() as session:
        friends = await get_friends(session, uid)

    await _safe_edit(query, get_friends_list_text(friends), get_friends_list_keyboard())


# ──────────────────────────────────────────────
# Пригласить друга
# ──────────────────────────────────────────────

async def open_invite(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    uid      = update.effective_user.id
    bot_name = (await context.bot.get_me()).username
    link     = f"t.me/{bot_name}?start=invite_{uid}"
    await _safe_edit(query, get_invite_text(bot_name, uid), get_invite_keyboard(link, back_cb=CB_FRIENDS))


# ──────────────────────────────────────────────
# Достижения (placeholder)
# ──────────────────────────────────────────────

# ──────────────────────────────────────────────
# Регистрация
# ──────────────────────────────────────────────

def register(app: Application) -> None:
    mapping = [
        (CB_FRIENDS,     open_friends_hub),
        (CB_FRI_RATING,  open_rating),
        (CB_FRI_LIST,    open_friends_list),
        (CB_FRI_INVITE,  open_invite),
        (CB_FRI_ACHIEV,  open_achievements),
    ]
    for cb, handler in mapping:
        app.add_handler(CallbackQueryHandler(handler, pattern=f"^{re.escape(cb)}$"))
