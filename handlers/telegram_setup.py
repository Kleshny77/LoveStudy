import logging

from telegram import (
    BotCommand,
    BotCommandScopeAllPrivateChats,
    MenuButtonCommands,
    Update,
)
from telegram.constants import ChatType, ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

from db.repositories import (
    get_friends,
    get_friends_rating,
    get_learning_streak_days,
    get_or_create_user,
    get_pomo_settings,
    get_profile_overview,
    get_upcoming_deadlines,
    list_active_deadlines,
    list_deadline_subjects,
)
from services.deadlines import get_deadlines_hub_keyboard, get_deadlines_hub_text
from services.friends import get_hub_keyboard, get_hub_no_friends_text, get_hub_text
from services.main_menu import (
    get_main_menu_keyboard,
    get_main_menu_text,
    get_materials_hub_keyboard,
    get_materials_hub_text,
)
from services.pomodoro import get_focus_menu_keyboard, get_focus_menu_text
from services.profile import get_profile_hub_keyboard, get_profile_hub_text
from services.telegram_setup import (
    get_deadline_notification_keyboard,
    get_group_redirect_keyboard,
    get_group_redirect_text,
    get_help_text,
    get_today_keyboard,
    get_today_text,
)

logger = logging.getLogger(__name__)
_HTML = ParseMode.HTML


async def configure_telegram_ui(app: Application) -> None:
    me = await app.bot.get_me()
    app.bot_data["bot_username"] = me.username

    default_commands = [
        BotCommand("start", "Запустить бота"),
        BotCommand("menu", "Открыть главное меню"),
        BotCommand("help", "Подсказка по командам"),
    ]
    private_commands = [
        BotCommand("menu", "Главное меню"),
        BotCommand("profile", "Профиль и статистика"),
        BotCommand("materials", "Материалы и предметы"),
        BotCommand("focus", "Помодоро"),
        BotCommand("deadlines", "Дедлайны"),
        BotCommand("friends", "Друзья и рейтинг"),
        BotCommand("today", "Краткая сводка"),
        BotCommand("help", "Подсказка по командам"),
    ]

    await app.bot.set_my_commands(default_commands)
    await app.bot.set_my_commands(private_commands, scope=BotCommandScopeAllPrivateChats())
    await app.bot.set_chat_menu_button(menu_button=MenuButtonCommands())


def _bot_username(context: ContextTypes.DEFAULT_TYPE) -> str | None:
    return context.bot_data.get("bot_username")


async def _ensure_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_user:
        return
    session_factory = context.bot_data.get("session_factory")
    if session_factory is None:
        return
    async with session_factory() as session:
        await get_or_create_user(
            session,
            telegram_id=update.effective_user.id,
            username=update.effective_user.username,
            first_name=update.effective_user.first_name,
        )


async def _redirect_to_private(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_chat:
        return
    await update.effective_chat.send_message(
        get_group_redirect_text(_bot_username(context)),
        reply_markup=get_group_redirect_keyboard(_bot_username(context)),
        parse_mode=_HTML,
    )


def _is_private(update: Update) -> bool:
    return bool(update.effective_chat and update.effective_chat.type == ChatType.PRIVATE)


async def cmd_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_private(update):
        await _redirect_to_private(update, context)
        return
    await _ensure_user(update, context)
    name = update.effective_user.first_name if update.effective_user else None
    await update.effective_chat.send_message(
        get_main_menu_text(name),
        reply_markup=get_main_menu_keyboard(),
        parse_mode=_HTML,
    )


async def cmd_materials(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_private(update):
        await _redirect_to_private(update, context)
        return
    await update.effective_chat.send_message(
        get_materials_hub_text(),
        reply_markup=get_materials_hub_keyboard(),
        parse_mode=_HTML,
    )


async def cmd_profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_private(update):
        await _redirect_to_private(update, context)
        return
    await _ensure_user(update, context)
    async with context.bot_data["session_factory"]() as session:
        overview = await get_profile_overview(session, update.effective_user.id)
    if overview is None:
        await update.effective_chat.send_message("Профиль пока недоступен.")
        return
    await update.effective_chat.send_message(
        get_profile_hub_text(overview),
        reply_markup=get_profile_hub_keyboard(),
        parse_mode=_HTML,
    )


async def cmd_focus(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_private(update):
        await _redirect_to_private(update, context)
        return
    await _ensure_user(update, context)
    async with context.bot_data["session_factory"]() as session:
        cfg = await get_pomo_settings(session, update.effective_user.id)
    await update.effective_chat.send_message(
        get_focus_menu_text(cfg.work_minutes, cfg.break_minutes, cfg.sessions_today),
        reply_markup=get_focus_menu_keyboard(),
        parse_mode=_HTML,
    )


async def cmd_deadlines(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_private(update):
        await _redirect_to_private(update, context)
        return
    await _ensure_user(update, context)
    async with context.bot_data["session_factory"]() as session:
        active_items = await list_active_deadlines(session, update.effective_user.id)
        subjects = await list_deadline_subjects(session, update.effective_user.id)
    await update.effective_chat.send_message(
        get_deadlines_hub_text(active_items),
        reply_markup=get_deadlines_hub_keyboard(subjects),
        parse_mode=_HTML,
    )


async def cmd_friends(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_private(update):
        await _redirect_to_private(update, context)
        return
    await _ensure_user(update, context)
    uid = update.effective_user.id
    async with context.bot_data["session_factory"]() as session:
        friends = await get_friends(session, uid)
        rating = await get_friends_rating(session, uid)

    friends_count = len(friends)
    my_rank = next((r for u, r in rating if u.telegram_id == uid), 1)
    total = len(rating)
    me_obj = next((u for u, _ in rating if u.telegram_id == uid), None)
    streak = get_learning_streak_days(me_obj)

    if friends_count == 0:
        bot_name = _bot_username(context)
        invite_link = f"t.me/{bot_name}?start=invite_{uid}" if bot_name else ""
        text = get_hub_no_friends_text()
        keyboard = get_hub_keyboard(has_friends=False, invite_link=invite_link)
    else:
        text = get_hub_text(streak, friends_count, my_rank, total)
        keyboard = get_hub_keyboard(has_friends=True)

    await update.effective_chat.send_message(text, reply_markup=keyboard, parse_mode=_HTML)


async def cmd_today(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_private(update):
        await _redirect_to_private(update, context)
        return
    await _ensure_user(update, context)
    uid = update.effective_user.id
    async with context.bot_data["session_factory"]() as session:
        overview = await get_profile_overview(session, uid)
        upcoming = await get_upcoming_deadlines(session, uid, days_ahead=3)

    if overview is None:
        await update.effective_chat.send_message("Сводка пока недоступна.")
        return

    upcoming_lines = [
        f"• {subject_name}: {deadline.title} — {deadline.due_at.strftime('%d.%m %H:%M')}"
        for deadline, subject_name in upcoming[:5]
    ]
    await update.effective_chat.send_message(
        get_today_text(
            upcoming_lines=upcoming_lines,
            focus_sessions_total=overview.total_focus_sessions,
            materials_total=overview.materials_count,
            subjects_total=overview.subjects_count,
        ),
        reply_markup=get_today_keyboard(),
        parse_mode=_HTML,
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_private(update):
        await _redirect_to_private(update, context)
        return
    await update.effective_chat.send_message(get_help_text(), parse_mode=_HTML)


def register(app: Application) -> None:
    app.add_handler(CommandHandler("menu", cmd_menu))
    app.add_handler(CommandHandler("materials", cmd_materials))
    app.add_handler(CommandHandler("profile", cmd_profile))
    app.add_handler(CommandHandler("focus", cmd_focus))
    app.add_handler(CommandHandler("deadlines", cmd_deadlines))
    app.add_handler(CommandHandler("friends", cmd_friends))
    app.add_handler(CommandHandler("today", cmd_today))
    app.add_handler(CommandHandler("help", cmd_help))
