import re

from telegram import Update
from telegram.constants import ParseMode
from telegram.error import BadRequest
from telegram.ext import Application, CallbackQueryHandler, ContextTypes

from constants import (
    CB_ACH_BACK,
    CB_ACH_DEADLINES,
    CB_ACH_DISCIPLINE,
    CB_ACH_HUB,
    CB_ACH_MATERIALS,
    CB_ACH_SERIES,
    CB_FRIENDS,
    CB_MAIN_PROFILE,
    UD_ACH_BACK_CB,
)
from db.repositories import get_achievements_overview
from services.achievements import (
    get_achievement_category_keyboard,
    get_achievement_category_text,
    get_achievements_hub_keyboard,
    get_achievements_hub_text,
)

_HTML = ParseMode.HTML


async def _safe_edit(query, text: str, keyboard) -> None:
    try:
        await query.edit_message_text(text, reply_markup=keyboard, parse_mode=_HTML)
    except BadRequest:
        await query.message.reply_text(text, reply_markup=keyboard, parse_mode=_HTML)


def _set_back(context: ContextTypes.DEFAULT_TYPE, back_cb: str) -> None:
    context.user_data[UD_ACH_BACK_CB] = back_cb


def _get_back(context: ContextTypes.DEFAULT_TYPE) -> str:
    return context.user_data.get(UD_ACH_BACK_CB, CB_MAIN_PROFILE)


async def _render_hub(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid = query.from_user.id
    async with context.bot_data["session_factory"]() as session:
        overview = await get_achievements_overview(session, uid)

    if overview is None:
        await query.answer("Достижения пока недоступны", show_alert=True)
        return

    await _safe_edit(query, get_achievements_hub_text(overview), get_achievements_hub_keyboard())


async def open_from_profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    _set_back(context, CB_MAIN_PROFILE)
    await _render_hub(query, context)


async def open_from_friends(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    _set_back(context, CB_FRIENDS)
    await _render_hub(query, context)


async def back_from_hub(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    target = _get_back(context)

    if target == CB_FRIENDS:
        from handlers.friends import open_friends_hub

        await open_friends_hub(update, context)
        return

    from handlers.profile import open_profile_hub

    await open_profile_hub(update, context)


async def open_hub(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    await _render_hub(query, context)


async def _open_category(update: Update, context: ContextTypes.DEFAULT_TYPE, category_key: str) -> None:
    query = update.callback_query
    await query.answer()

    uid = update.effective_user.id
    async with context.bot_data["session_factory"]() as session:
        overview = await get_achievements_overview(session, uid)

    if overview is None:
        await query.answer("Достижения пока недоступны", show_alert=True)
        return

    category = next((item for item in overview.categories if item.key == category_key), None)
    if category is None:
        await query.answer("Категория не найдена", show_alert=True)
        return

    await _safe_edit(query, get_achievement_category_text(category), get_achievement_category_keyboard())


async def open_discipline(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _open_category(update, context, "discipline")


async def open_deadlines(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _open_category(update, context, "deadlines")


async def open_materials(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _open_category(update, context, "materials")


async def open_series(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _open_category(update, context, "series")


def register(app: Application) -> None:
    mapping = [
        (CB_ACH_BACK, back_from_hub),
        (CB_ACH_HUB, open_hub),
        (CB_ACH_DISCIPLINE, open_discipline),
        (CB_ACH_DEADLINES, open_deadlines),
        (CB_ACH_MATERIALS, open_materials),
        (CB_ACH_SERIES, open_series),
    ]
    for cb, handler in mapping:
        app.add_handler(CallbackQueryHandler(handler, pattern=rf"^{re.escape(cb)}$"))
