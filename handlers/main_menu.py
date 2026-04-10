# коллбэки главного меню и глобальная навигация «назад в главное меню»

import logging

from telegram import Update
from telegram.error import BadRequest
from telegram.ext import Application, CallbackQueryHandler, ContextTypes

from constants import CB_MAIN_DEADLINES, CB_MAIN_MATERIALS, CB_MAIN_PROFILE, CB_MAIN_SUBJECTS, CB_MAT_TO_MAIN, CB_NAV_HUB, CB_NAV_MAIN, CB_NAV_SUBS
from handlers.subjects import send_subjects_screen
from services.analytics import EV_OPEN_SCREEN, schedule_track
from services.callback_feedback import answer_callback
from services.main_menu import get_main_menu_keyboard, get_main_menu_text, get_materials_hub_keyboard, get_materials_hub_text

logger = logging.getLogger(__name__)


async def main_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    uid = update.effective_user.id if update.effective_user else None

    if query.data == CB_MAIN_MATERIALS:
        schedule_track(context, uid, EV_OPEN_SCREEN, {"screen": "materials_hub"})
        await answer_callback(query)
        await query.edit_message_text(
            get_materials_hub_text(),
            reply_markup=get_materials_hub_keyboard(),
            parse_mode="HTML",
        )
    elif query.data == CB_MAIN_SUBJECTS:
        schedule_track(context, uid, EV_OPEN_SCREEN, {"screen": "subjects"})
        await send_subjects_screen(update, context)
    elif query.data == CB_MAIN_PROFILE:
        schedule_track(context, uid, EV_OPEN_SCREEN, {"screen": "profile"})
        from handlers.profile import open_profile_hub
        await open_profile_hub(update, context)
    elif query.data == CB_MAIN_DEADLINES:
        schedule_track(context, uid, EV_OPEN_SCREEN, {"screen": "deadlines"})
        from handlers.deadlines import open_deadlines_hub
        await open_deadlines_hub(update, context)
    elif query.data == "main:friends":
        schedule_track(context, uid, EV_OPEN_SCREEN, {"screen": "friends"})
        from handlers.friends import open_friends_hub
        await open_friends_hub(update, context)
    elif query.data == "main:pomodoro":
        schedule_track(context, uid, EV_OPEN_SCREEN, {"screen": "pomodoro"})
        from handlers.pomodoro import open_pomodoro
        await open_pomodoro(update, context)


async def go_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await answer_callback(query)
    name = update.effective_user.first_name if update.effective_user else None
    text = get_main_menu_text(name)
    keyboard = get_main_menu_keyboard()
    try:
        await query.edit_message_text(
            text,
            reply_markup=keyboard,
            parse_mode="HTML",
        )
    except BadRequest:
        try:
            await query.edit_message_reply_markup(reply_markup=None)
        except Exception:
            pass
        await update.effective_chat.send_message(
            text,
            reply_markup=keyboard,
            parse_mode="HTML",
        )


async def go_to_hub(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """← Назад к экрану «Мои предметы» (hub)."""
    query = update.callback_query
    await answer_callback(query)
    await query.edit_message_text(
        get_materials_hub_text(),
        reply_markup=get_materials_hub_keyboard(),
        parse_mode="HTML",
    )


async def go_to_subjects(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """← Назад к списку предметов."""
    query = update.callback_query
    await send_subjects_screen(update, context)


def register(app: Application) -> None:
    app.add_handler(CallbackQueryHandler(main_menu_callback, pattern=r"^main:"))
    app.add_handler(CallbackQueryHandler(go_to_main, pattern=rf"^({CB_NAV_MAIN}|{CB_MAT_TO_MAIN})$"))
    app.add_handler(CallbackQueryHandler(go_to_hub, pattern=rf"^{CB_NAV_HUB}$"))
    app.add_handler(CallbackQueryHandler(go_to_subjects, pattern=rf"^{CB_NAV_SUBS}$"))
