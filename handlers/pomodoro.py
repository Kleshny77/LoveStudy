# Полный флоу помодоро: фокус, пауза, перерыв, цикл, настройки.
#
# Таймер реализован через PTB job_queue:
#   - run_repeating(_tick, 30s)  — обновляет счётчик в сообщении
#   - run_once(_phase_done, N с) — срабатывает по окончании фазы
#
# Состояние активной сессии хранится в application.bot_data["pomo"][user_id].
# Настройки (интервалы, напоминания и т.д.) хранятся в БД.

import logging
import re
from datetime import datetime, timedelta, timezone

from telegram import Update
from telegram.constants import ParseMode
from telegram.error import BadRequest
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from constants import (
    CB_NAV_MAIN,
    CB_POMO_AUT_OFF, CB_POMO_AUT_ON,
    CB_POMO_AUTO, CB_POMO_CFG, CB_POMO_CUSTOM,
    CB_POMO_NEXT, CB_POMO_NOTIF, CB_POMO_OPEN,
    CB_POMO_PAUSE, CB_POMO_PRESET,
    CB_POMO_REM_OFF, CB_POMO_REM_ON, CB_POMO_REMIND,
    CB_POMO_RESUME, CB_POMO_SKIP, CB_POMO_START, CB_POMO_STOP,
    ST_POMO_CUSTOM,
)
from db.repositories import (
    get_pomo_settings,
    increment_pomo_sessions,
    save_pomo_settings,
)
from services.pomodoro import (
    get_auto_toggle_keyboard,
    get_break_timer_keyboard,
    get_break_timer_text,
    get_custom_input_keyboard,
    get_custom_input_text,
    get_cycle_done_keyboard,
    get_cycle_done_text,
    get_focus_menu_keyboard,
    get_focus_menu_text,
    get_interval_cfg_keyboard,
    get_interval_cfg_text,
    get_notif_settings_keyboard,
    get_notif_settings_text,
    get_paused_keyboard,
    get_paused_text,
    get_reminder_toggle_keyboard,
    get_work_done_text,
    get_work_timer_keyboard,
    get_work_timer_text,
)

logger = logging.getLogger(__name__)

# ключ в bot_data для хранения активных сессий
_POMO_KEY = "pomo"


# ──────────────────────────────────────────────
# Вспомогательные функции
# ──────────────────────────────────────────────

def _get_state(bot_data: dict, user_id: int) -> dict | None:
    return bot_data.get(_POMO_KEY, {}).get(user_id)


def _set_state(bot_data: dict, user_id: int, state: dict) -> None:
    bot_data.setdefault(_POMO_KEY, {})[user_id] = state


def _clear_state(bot_data: dict, user_id: int) -> None:
    bot_data.get(_POMO_KEY, {}).pop(user_id, None)


def _cancel_jobs(job_queue, user_id: int) -> None:
    for name in (f"pomo_tick_{user_id}", f"pomo_done_{user_id}"):
        for job in job_queue.get_jobs_by_name(name):
            job.schedule_removal()


def _remaining(state: dict) -> int:
    """Оставшееся время в секундах для текущей фазы."""
    end: datetime = state["end_time"]
    return int((end - datetime.now(timezone.utc)).total_seconds())


async def _safe_edit(bot, chat_id: int, msg_id: int, text: str, keyboard) -> None:
    try:
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=msg_id,
            text=text,
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML,
        )
    except BadRequest:
        pass  # сообщение уже удалено или текст не изменился


# ──────────────────────────────────────────────
# Job-колбэки (вызываются планировщиком)
# ──────────────────────────────────────────────

async def _tick(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обновляет отображение таймера каждые 30 секунд."""
    user_id = context.job.data
    state = _get_state(context.bot_data, user_id)
    if not state or state.get("paused"):
        return

    remaining = _remaining(state)
    if remaining <= 0:
        return

    phase = state["phase"]
    if phase == "work":
        text, kbd = get_work_timer_text(remaining), get_work_timer_keyboard()
    else:
        text, kbd = get_break_timer_text(remaining), get_break_timer_keyboard()

    await _safe_edit(context.bot, state["chat_id"], state["msg_id"], text, kbd)


async def _phase_done(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Срабатывает по окончании фазы (работа или перерыв)."""
    user_id = context.job.data
    state = _get_state(context.bot_data, user_id)
    if not state:
        return

    phase = state["phase"]
    chat_id = state["chat_id"]

    # Отменяем тик-джоб
    _cancel_jobs(context.job_queue, user_id)

    if phase == "work":
        work_min  = state["work_min"]
        break_min = state["break_min"]

        # Обновляем сообщение-таймер: убираем кнопки
        await _safe_edit(
            context.bot, chat_id, state["msg_id"],
            get_work_timer_text(0), None,
        )

        # Уведомление об окончании работы
        await context.bot.send_message(
            chat_id=chat_id,
            text=get_work_done_text(work_min, break_min),
            parse_mode=ParseMode.HTML,
        )

        # Запускаем перерыв (отдельное сообщение с таймером)
        break_sec = break_min * 60
        now = datetime.now(timezone.utc)
        msg = await context.bot.send_message(
            chat_id=chat_id,
            text=get_break_timer_text(break_sec),
            reply_markup=get_break_timer_keyboard(),
            parse_mode=ParseMode.HTML,
        )

        state["phase"]    = "break"
        state["msg_id"]   = msg.message_id
        state["end_time"] = now + timedelta(seconds=break_sec)
        _set_state(context.bot_data, user_id, state)

        _schedule_jobs(context.job_queue, user_id, break_sec)

    else:  # break done → cycle complete
        # Увеличиваем счётчик сессий в БД
        sessions = state.get("sessions_today", 0) + 1
        try:
            async with context.bot_data["session_factory"]() as session:
                sessions = await increment_pomo_sessions(
                    session,
                    user_id,
                    work_minutes=state.get("work_min"),
                )
        except Exception:
            logger.exception("Ошибка при инкременте сессий помодоро")

        # Убираем кнопки с сообщения-таймера
        await _safe_edit(
            context.bot, chat_id, state["msg_id"],
            get_break_timer_text(0), None,
        )

        # Сообщение о завершении цикла
        await context.bot.send_message(
            chat_id=chat_id,
            text=get_cycle_done_text(sessions),
            reply_markup=get_cycle_done_keyboard(),
            parse_mode=ParseMode.HTML,
        )

        _clear_state(context.bot_data, user_id)


_TICK_INTERVAL = 1  # секунд между обновлениями таймера в сообщении


def _schedule_jobs(job_queue, user_id: int, duration_sec: int) -> None:
    if job_queue is None:
        logger.error(
            "job_queue = None — apscheduler не установлен! "
            "Установи: pip install 'python-telegram-bot[job-queue]'"
        )
        return
    job_queue.run_repeating(
        _tick,
        interval=_TICK_INTERVAL,
        first=_TICK_INTERVAL,
        name=f"pomo_tick_{user_id}",
        data=user_id,
    )
    job_queue.run_once(
        _phase_done,
        when=duration_sec,
        name=f"pomo_done_{user_id}",
        data=user_id,
    )


# ──────────────────────────────────────────────
# Утилита: вернуть фокус-экран (используется в нескольких местах)
# ──────────────────────────────────────────────

async def _show_focus_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, edit: bool = True) -> None:
    uid = update.effective_user.id
    async with context.bot_data["session_factory"]() as session:
        cfg = await get_pomo_settings(session, uid)

    text = get_focus_menu_text(cfg.work_minutes, cfg.break_minutes, cfg.sessions_today)
    kbd  = get_focus_menu_keyboard()

    if edit and update.callback_query:
        try:
            await update.callback_query.edit_message_text(text, reply_markup=kbd, parse_mode=ParseMode.HTML)
        except BadRequest:
            await update.effective_chat.send_message(text, reply_markup=kbd, parse_mode=ParseMode.HTML)
    else:
        await update.effective_chat.send_message(text, reply_markup=kbd, parse_mode=ParseMode.HTML)


# ──────────────────────────────────────────────
# Точки входа
# ──────────────────────────────────────────────

async def open_pomodoro(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Открыть фокус-экран (из главного меню или после «В меню»)."""
    query = update.callback_query
    await query.answer()
    await _show_focus_menu(update, context, edit=True)


# ──────────────────────────────────────────────
# Управление таймером
# ──────────────────────────────────────────────

async def start_focus(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Начать рабочую фазу."""
    query = update.callback_query
    await query.answer()

    uid     = update.effective_user.id
    chat_id = update.effective_chat.id
    logger.info("start_focus called: uid=%s chat=%s job_queue=%s", uid, chat_id, context.job_queue)

    try:
        # Если сессия уже идёт — игнорируем
        if _get_state(context.bot_data, uid):
            logger.info("start_focus: session already running for uid=%s, skipping", uid)
            return

        async with context.bot_data["session_factory"]() as session:
            cfg = await get_pomo_settings(session, uid)

        work_sec = cfg.work_minutes * 60
        now      = datetime.now(timezone.utc)

        text = get_work_timer_text(work_sec)
        kbd  = get_work_timer_keyboard()

        try:
            await query.edit_message_text(text, reply_markup=kbd, parse_mode=ParseMode.HTML)
            msg_id = query.message.message_id
        except BadRequest:
            msg = await context.bot.send_message(chat_id, text, reply_markup=kbd, parse_mode=ParseMode.HTML)
            msg_id = msg.message_id

        logger.info("start_focus: timer message set, msg_id=%s", msg_id)

        _set_state(context.bot_data, uid, {
            "phase":          "work",
            "chat_id":        chat_id,
            "msg_id":         msg_id,
            "end_time":       now + timedelta(seconds=work_sec),
            "work_min":       cfg.work_minutes,
            "break_min":      cfg.break_minutes,
            "auto_break":     cfg.auto_break,
            "paused":         False,
            "sessions_today": cfg.sessions_today,
            "user_name":      update.effective_user.first_name or update.effective_user.username or "Твой друг",
        })

        _schedule_jobs(context.job_queue, uid, work_sec)
        logger.info("start_focus: jobs scheduled for uid=%s, duration=%ss", uid, work_sec)

    except Exception:
        logger.exception("start_focus FAILED for uid=%s", uid)
        raise


async def pause_timer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    uid   = update.effective_user.id
    state = _get_state(context.bot_data, uid)
    if not state or state.get("paused"):
        return

    remaining = _remaining(state)
    _cancel_jobs(context.job_queue, uid)

    state["paused"]           = True
    state["paused_remaining"] = remaining
    _set_state(context.bot_data, uid, state)

    await _safe_edit(
        context.bot, state["chat_id"], state["msg_id"],
        get_paused_text(remaining), get_paused_keyboard(),
    )


async def resume_timer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    uid   = update.effective_user.id
    state = _get_state(context.bot_data, uid)
    if not state or not state.get("paused"):
        return

    remaining = state["paused_remaining"]
    now       = datetime.now(timezone.utc)

    state["paused"]   = False
    state["end_time"] = now + timedelta(seconds=remaining)
    _set_state(context.bot_data, uid, state)

    phase = state["phase"]
    if phase == "work":
        text, kbd = get_work_timer_text(remaining), get_work_timer_keyboard()
    else:
        text, kbd = get_break_timer_text(remaining), get_break_timer_keyboard()

    await _safe_edit(context.bot, state["chat_id"], state["msg_id"], text, kbd)
    _schedule_jobs(context.job_queue, uid, remaining)


async def stop_timer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Досрочно завершить сессию."""
    query = update.callback_query
    await query.answer()

    uid   = update.effective_user.id
    state = _get_state(context.bot_data, uid)

    _cancel_jobs(context.job_queue, uid)
    _clear_state(context.bot_data, uid)

    if state:
        await _safe_edit(context.bot, state["chat_id"], state["msg_id"],
                         "🛑 <b>Сессия завершена.</b>", None)

    await _show_focus_menu(update, context, edit=False)


async def skip_break(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Пропустить перерыв — считаем цикл завершённым."""
    query = update.callback_query
    await query.answer()

    uid   = update.effective_user.id
    state = _get_state(context.bot_data, uid)

    _cancel_jobs(context.job_queue, uid)

    sessions = state.get("sessions_today", 0) + 1 if state else 1
    try:
        async with context.bot_data["session_factory"]() as session:
            sessions = await increment_pomo_sessions(
                session,
                uid,
                work_minutes=state.get("work_min") if state else None,
            )
    except Exception:
        logger.exception("Ошибка при инкременте сессий (skip_break)")

    if state:
        await _safe_edit(context.bot, state["chat_id"], state["msg_id"],
                         get_break_timer_text(0), None)

    _clear_state(context.bot_data, uid)

    await update.effective_chat.send_message(
        get_cycle_done_text(sessions),
        reply_markup=get_cycle_done_keyboard(),
        parse_mode=ParseMode.HTML,
    )


async def next_cycle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Начать следующий цикл (из экрана «Цикл завершён»)."""
    query = update.callback_query
    await query.answer()

    uid     = update.effective_user.id
    chat_id = update.effective_chat.id

    async with context.bot_data["session_factory"]() as session:
        cfg = await get_pomo_settings(session, uid)

    work_sec = cfg.work_minutes * 60
    now      = datetime.now(timezone.utc)

    # Отправляем новое сообщение-таймер
    msg = await context.bot.send_message(
        chat_id,
        get_work_timer_text(work_sec),
        reply_markup=get_work_timer_keyboard(),
        parse_mode=ParseMode.HTML,
    )

    _set_state(context.bot_data, uid, {
        "phase":          "work",
        "chat_id":        chat_id,
        "msg_id":         msg.message_id,
        "end_time":       now + timedelta(seconds=work_sec),
        "work_min":       cfg.work_minutes,
        "break_min":      cfg.break_minutes,
        "auto_break":     cfg.auto_break,
        "paused":         False,
        "sessions_today": cfg.sessions_today,
    })

    _schedule_jobs(context.job_queue, uid, work_sec)


# ──────────────────────────────────────────────
# Настройка интервалов
# ──────────────────────────────────────────────

async def open_interval_cfg(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    try:
        await query.edit_message_text(
            get_interval_cfg_text(),
            reply_markup=get_interval_cfg_keyboard(),
            parse_mode=ParseMode.HTML,
        )
    except BadRequest:
        await update.effective_chat.send_message(
            get_interval_cfg_text(),
            reply_markup=get_interval_cfg_keyboard(),
            parse_mode=ParseMode.HTML,
        )


async def apply_preset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Применить пресет работа/перерыв."""
    query = update.callback_query
    await query.answer()

    # callback_data = "pom:pre:<work>:<break>"
    data = query.data[len("pom:pre:"):]
    work_str, break_str = data.split(":")
    work_min  = int(work_str)
    break_min = int(break_str)

    uid = update.effective_user.id
    async with context.bot_data["session_factory"]() as session:
        await save_pomo_settings(session, uid, work_minutes=work_min, break_minutes=break_min)

    # Возвращаем на фокус-экран с обновлёнными настройками
    await _show_focus_menu(update, context, edit=True)


async def open_custom_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Открыть экран ввода ручного интервала (вход в ConversationHandler)."""
    query = update.callback_query
    await query.answer()
    try:
        await query.edit_message_text(
            get_custom_input_text(),
            reply_markup=get_custom_input_keyboard(),
            parse_mode=ParseMode.HTML,
        )
    except BadRequest:
        await update.effective_chat.send_message(
            get_custom_input_text(),
            reply_markup=get_custom_input_keyboard(),
            parse_mode=ParseMode.HTML,
        )
    return ST_POMO_CUSTOM


async def receive_custom_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получить текстовый ввод пользователя с ручным интервалом."""
    text = (update.message.text or "").strip()
    match = re.fullmatch(r"\s*(\d+)\s*/\s*(\d+)\s*", text)

    if not match:
        await update.message.reply_text(
            "Неверный формат. Введи два числа через /\n"
            "<i>Например: 40/15</i>",
            parse_mode=ParseMode.HTML,
        )
        return ST_POMO_CUSTOM

    work_min  = int(match.group(1))
    break_min = int(match.group(2))

    if not (1 <= work_min <= 180) or not (1 <= break_min <= 60):
        await update.message.reply_text(
            "Работа: 1–180 мин, перерыв: 1–60 мин. Попробуй ещё раз.",
        )
        return ST_POMO_CUSTOM

    uid = update.effective_user.id
    async with context.bot_data["session_factory"]() as session:
        await save_pomo_settings(session, uid, work_minutes=work_min, break_minutes=break_min)

    await update.message.reply_text(
        f"✅ Сохранено: <b>{work_min} / {break_min}</b>",
        parse_mode=ParseMode.HTML,
    )
    await _show_focus_menu(update, context, edit=False)
    return ConversationHandler.END


async def cancel_custom_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Выход из ручного ввода — возврат к настройкам интервалов."""
    query = update.callback_query
    await query.answer()
    try:
        await query.edit_message_text(
            get_interval_cfg_text(),
            reply_markup=get_interval_cfg_keyboard(),
            parse_mode=ParseMode.HTML,
        )
    except BadRequest:
        await update.effective_chat.send_message(
            get_interval_cfg_text(),
            reply_markup=get_interval_cfg_keyboard(),
            parse_mode=ParseMode.HTML,
        )
    return ConversationHandler.END


# ──────────────────────────────────────────────
# Настройки уведомлений
# ──────────────────────────────────────────────

async def open_notif_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    uid = update.effective_user.id
    async with context.bot_data["session_factory"]() as session:
        cfg = await get_pomo_settings(session, uid)

    text = get_notif_settings_text(cfg.reminder_enabled, cfg.auto_break)
    kbd  = get_notif_settings_keyboard()
    try:
        await query.edit_message_text(text, reply_markup=kbd, parse_mode=ParseMode.HTML)
    except BadRequest:
        await update.effective_chat.send_message(text, reply_markup=kbd, parse_mode=ParseMode.HTML)


async def open_reminder_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    try:
        await query.edit_message_text(
            "📳 Напоминание за 1 минуту до конца",
            reply_markup=get_reminder_toggle_keyboard(),
        )
    except BadRequest:
        await update.effective_chat.send_message(
            "📳 Напоминание за 1 минуту до конца",
            reply_markup=get_reminder_toggle_keyboard(),
        )


async def open_auto_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    try:
        await query.edit_message_text(
            "🔄 Автоматически запускать перерыв",
            reply_markup=get_auto_toggle_keyboard(),
        )
    except BadRequest:
        await update.effective_chat.send_message(
            "🔄 Автоматически запускать перерыв",
            reply_markup=get_auto_toggle_keyboard(),
        )


async def _save_notif_and_show(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    **kwargs,
) -> None:
    uid = update.effective_user.id
    async with context.bot_data["session_factory"]() as session:
        cfg = await save_pomo_settings(session, uid, **kwargs)

    text = get_notif_settings_text(cfg.reminder_enabled, cfg.auto_break)
    kbd  = get_notif_settings_keyboard()
    try:
        await update.callback_query.edit_message_text(text, reply_markup=kbd, parse_mode=ParseMode.HTML)
    except BadRequest:
        await update.effective_chat.send_message(text, reply_markup=kbd, parse_mode=ParseMode.HTML)


async def set_reminder_on(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.callback_query.answer()
    await _save_notif_and_show(update, context, reminder_enabled=True)


async def set_reminder_off(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.callback_query.answer()
    await _save_notif_and_show(update, context, reminder_enabled=False)


async def set_auto_on(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.callback_query.answer()
    await _save_notif_and_show(update, context, auto_break=True)


async def set_auto_off(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.callback_query.answer()
    await _save_notif_and_show(update, context, auto_break=False)


# ──────────────────────────────────────────────
# Регистрация хэндлеров
# ──────────────────────────────────────────────

def register(app: Application) -> None:
    # ConversationHandler только для ручного ввода интервала
    custom_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(open_custom_input, pattern=f"^{CB_POMO_CUSTOM}$")],
        states={
            ST_POMO_CUSTOM: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_custom_input),
            ],
        },
        fallbacks=[
            CallbackQueryHandler(cancel_custom_input, pattern=f"^{CB_POMO_CFG}$"),
            CallbackQueryHandler(open_pomodoro,        pattern=f"^{CB_POMO_OPEN}$"),
        ],
        per_message=False,
    )
    app.add_handler(custom_conv)

    # Обычные callback-хэндлеры
    mapping = [
        (CB_POMO_OPEN,    open_pomodoro),
        (CB_POMO_START,   start_focus),
        (CB_POMO_PAUSE,   pause_timer),
        (CB_POMO_RESUME,  resume_timer),
        (CB_POMO_STOP,    stop_timer),
        (CB_POMO_SKIP,    skip_break),
        (CB_POMO_NEXT,    next_cycle),
        (CB_POMO_CFG,     open_interval_cfg),
        (CB_POMO_NOTIF,   open_notif_settings),
        (CB_POMO_REMIND,  open_reminder_toggle),
        (CB_POMO_AUTO,    open_auto_toggle),
        (CB_POMO_REM_ON,  set_reminder_on),
        (CB_POMO_REM_OFF, set_reminder_off),
        (CB_POMO_AUT_ON,  set_auto_on),
        (CB_POMO_AUT_OFF, set_auto_off),
    ]
    for cb, handler in mapping:
        app.add_handler(CallbackQueryHandler(handler, pattern=f"^{re.escape(cb)}$"))

    # Пресет-выборщик (callback_data начинается с "pom:pre:")
    app.add_handler(CallbackQueryHandler(apply_preset, pattern=r"^pom:pre:\d+:\d+$"))
