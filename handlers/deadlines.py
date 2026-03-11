import logging
import re
from datetime import date, datetime, time, timezone

from sqlalchemy import select
from telegram import Update
from telegram.constants import ParseMode
from telegram.error import BadRequest
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from constants import (
    CB_DDL_ACTION_DELETE,
    CB_DDL_ACTION_DONE,
    CB_DDL_ACTION_MOVE,
    CB_DDL_ACTION_PICK,
    CB_DDL_ACTION_REMIND,
    CB_DDL_BACK_HUB,
    CB_DDL_BACK_SUBJECT,
    CB_DDL_BACK_SUBJECTS,
    CB_DDL_CREATE,
    CB_DDL_EDIT_DATE,
    CB_DDL_EDIT_DONE,
    CB_DDL_EDIT_SUBJECT,
    CB_DDL_EDIT_TIME,
    CB_DDL_EDIT_TITLE,
    CB_DDL_NEW_SUBJECT,
    CB_DDL_REMIND_CUSTOM,
    CB_DDL_REMIND_SET,
    CB_DDL_REVIEW_CREATE,
    CB_DDL_REVIEW_EDIT,
    CB_DDL_SETTINGS,
    CB_DDL_SETTINGS_SAVE,
    CB_DDL_SET_OFF,
    CB_DDL_SET_ON,
    CB_DDL_STEP_DATE,
    CB_DDL_STEP_SUBJECT,
    CB_DDL_STEP_TIME,
    CB_DDL_STEP_TITLE,
    CB_DDL_SUBJECT,
    CB_DDL_SUBJECTS,
    CB_DDL_SUCCESS_SUBS,
    CB_DDL_TOGGLE_DAILY,
    CB_DDL_TOGGLE_MAIN,
    CB_MAIN_DEADLINES,
    CB_NAV_MAIN,
    ST_DDL_ACTION_INDEX,
    ST_DDL_DATE,
    ST_DDL_EDIT_MENU,
    ST_DDL_MOVE_DATE,
    ST_DDL_MOVE_TIME,
    ST_DDL_REMINDER_PICK,
    ST_DDL_REMINDER_CUSTOM,
    ST_DDL_REVIEW,
    ST_DDL_SETTINGS_KIND,
    ST_DDL_SETTINGS_MENU,
    ST_DDL_SETTINGS_TIME,
    ST_DDL_SUBJECT_NAME,
    ST_DDL_TIME,
    ST_DDL_TITLE,
    UD_DDL_ACTION,
    UD_DDL_DATE,
    UD_DDL_EDITING,
    UD_DDL_SETTINGS_KIND,
    UD_DDL_SUBJECT_ID,
    UD_DDL_SUBJECT_NAME,
    UD_DDL_TIME,
    UD_DDL_TITLE,
)
from db.repositories import (
    complete_deadline,
    create_deadline,
    get_deadline_settings,
    get_due_daily_digests,
    get_due_deadline_reminders,
    get_subject_by_id,
    list_active_deadlines,
    list_deadline_subjects,
    list_subject_deadlines,
    mark_daily_digest_sent,
    mark_deadline_reminder_sent,
    remove_deadline,
    reschedule_deadline,
    save_deadline_settings,
    set_deadline_reminder,
    get_upcoming_deadlines,
)
from db.models import Deadline, User
from services.deadlines import (
    get_deadline_action_choice_keyboard,
    get_deadline_action_choice_text,
    get_daily_digest_text,
    get_daily_time_text,
    get_deadline_custom_reminder_text,
    get_deadline_edit_menu_keyboard,
    get_deadline_edit_menu_text,
    get_deadline_reminder_choice_keyboard,
    get_deadline_reminder_choice_text,
    get_deadline_reminder_message,
    get_deadline_review_keyboard,
    get_deadline_review_text,
    get_deadline_settings_keyboard,
    get_deadline_settings_text,
    get_deadline_subjects_keyboard,
    get_deadline_subjects_text,
    get_deadline_success_keyboard,
    get_deadline_success_text,
    get_deadlines_hub_keyboard,
    get_deadlines_hub_text,
    get_date_step_text,
    get_single_back_keyboard,
    get_subject_deadlines_keyboard,
    get_subject_deadlines_text,
    get_subject_step_text,
    get_time_step_text,
    get_title_step_text,
    get_toggle_choice_keyboard,
    get_toggle_choice_text,
)
from services.telegram_setup import get_deadline_notification_keyboard

logger = logging.getLogger(__name__)
_HTML = ParseMode.HTML
_DEADLINE_ACTION_LABELS = {
    CB_DDL_ACTION_DONE: "выполнено",
    CB_DDL_ACTION_MOVE: "перенос",
    CB_DDL_ACTION_DELETE: "удаление",
    CB_DDL_ACTION_REMIND: "напоминание",
}
_DEADLINE_ACTION_CODES = {
    CB_DDL_ACTION_DONE: "d",
    CB_DDL_ACTION_MOVE: "m",
    CB_DDL_ACTION_DELETE: "x",
    CB_DDL_ACTION_REMIND: "r",
}
_DEADLINE_ACTION_BY_CODE = {value: key for key, value in _DEADLINE_ACTION_CODES.items()}


def _clear_deadline_draft(context: ContextTypes.DEFAULT_TYPE) -> None:
    for key in (
        UD_DDL_SUBJECT_ID,
        UD_DDL_SUBJECT_NAME,
        UD_DDL_TITLE,
        UD_DDL_DATE,
        UD_DDL_TIME,
        UD_DDL_EDITING,
        UD_DDL_ACTION,
        UD_DDL_SETTINGS_KIND,
        "ddl_action_deadline_id",
        "ddl_action_deadline_title",
        "ddl_move_date",
    ):
        context.user_data.pop(key, None)


def _parse_date(raw: str) -> date | None:
    try:
        return datetime.strptime(raw.strip(), "%d.%m.%Y").date()
    except ValueError:
        return None


def _parse_time(raw: str) -> time | None:
    try:
        return datetime.strptime(raw.strip(), "%H:%M").time()
    except ValueError:
        return None


def _build_due_at(context: ContextTypes.DEFAULT_TYPE) -> datetime:
    deadline_date = _parse_date(context.user_data[UD_DDL_DATE])
    deadline_time = _parse_time(context.user_data[UD_DDL_TIME])
    assert deadline_date is not None and deadline_time is not None
    return datetime.combine(deadline_date, deadline_time, tzinfo=timezone.utc)


def _is_past_due(due_at: datetime) -> bool:
    return due_at < datetime.now(timezone.utc)


def _parse_custom_reminder(raw: str) -> int | None:
    text = raw.strip().lower()
    if not text:
        return None
    match = re.fullmatch(r"\s*(?:(\d+)\s*д)?\s*(?:(\d+)\s*ч)?\s*(?:(\d+)\s*м)?\s*", text)
    if not match:
        return None
    days = int(match.group(1) or 0)
    hours = int(match.group(2) or 0)
    minutes = int(match.group(3) or 0)
    total_minutes = days * 24 * 60 + hours * 60 + minutes
    return total_minutes if total_minutes > 0 else None


async def _safe_edit(query, text: str, keyboard) -> None:
    try:
        await query.edit_message_text(text, reply_markup=keyboard, parse_mode=_HTML)
    except BadRequest:
        await query.message.reply_text(text, reply_markup=keyboard, parse_mode=_HTML)


async def _render_deadlines_hub(query, context: ContextTypes.DEFAULT_TYPE, user_id: int) -> None:
    async with context.bot_data["session_factory"]() as session:
        active_items = await list_active_deadlines(session, user_id, limit=5)
        subjects = await list_deadline_subjects(session, user_id)
    await _safe_edit(query, get_deadlines_hub_text(active_items), get_deadlines_hub_keyboard(subjects))


async def _render_deadline_subjects(query, context: ContextTypes.DEFAULT_TYPE, user_id: int) -> None:
    async with context.bot_data["session_factory"]() as session:
        subjects = await list_deadline_subjects(session, user_id)
    await _safe_edit(query, get_deadline_subjects_text(subjects), get_deadline_subjects_keyboard(subjects))


async def _render_subject_deadlines(query, context: ContextTypes.DEFAULT_TYPE, user_id: int, subject_id: int) -> None:
    async with context.bot_data["session_factory"]() as session:
        subject = await get_subject_by_id(session, subject_id, user_id)
        deadlines = await list_subject_deadlines(session, user_id, subject_id)

    if subject is None:
        await query.answer("Предмет не найден", show_alert=True)
        return

    context.user_data[UD_DDL_SUBJECT_ID] = subject.id
    context.user_data[UD_DDL_SUBJECT_NAME] = subject.name
    await _safe_edit(
        query,
        get_subject_deadlines_text(subject.name, deadlines),
        get_subject_deadlines_keyboard(has_deadlines=bool(deadlines)),
    )


async def open_deadlines_hub(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    await _render_deadlines_hub(query, context, update.effective_user.id)


async def open_deadline_subjects(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    await _render_deadline_subjects(query, context, update.effective_user.id)


async def open_subject_deadlines(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    subject_id = int(query.data.removeprefix(CB_DDL_SUBJECT))
    await _render_subject_deadlines(query, context, update.effective_user.id, subject_id)


async def back_to_deadlines_hub(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await _render_deadlines_hub(query, context, update.effective_user.id)
    return ConversationHandler.END


async def back_to_deadline_subjects(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await _render_deadline_subjects(query, context, update.effective_user.id)
    return ConversationHandler.END


async def back_to_subject_deadlines(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    subject_id = context.user_data.get(UD_DDL_SUBJECT_ID)
    if not subject_id:
        await _render_deadline_subjects(query, context, update.effective_user.id)
        return ConversationHandler.END
    await _render_subject_deadlines(query, context, update.effective_user.id, subject_id)
    return ConversationHandler.END


async def go_to_main_from_deadlines(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    from handlers.main_menu import go_to_main

    await go_to_main(update, context)
    return ConversationHandler.END


async def _show_subject_step(query, subject_back_cb: str) -> int:
    await _safe_edit(query, get_subject_step_text(), get_single_back_keyboard(subject_back_cb))
    return ST_DDL_SUBJECT_NAME


async def _show_title_step(query, context: ContextTypes.DEFAULT_TYPE, back_cb: str | None = None) -> int:
    actual_back = back_cb or (CB_DDL_STEP_SUBJECT if context.user_data.get(UD_DDL_SUBJECT_ID) is None else CB_DDL_BACK_SUBJECT)
    await _safe_edit(query, get_title_step_text(), get_single_back_keyboard(actual_back))
    return ST_DDL_TITLE


async def _show_date_step(query, back_cb: str = CB_DDL_STEP_TITLE) -> int:
    await _safe_edit(query, get_date_step_text(), get_single_back_keyboard(back_cb))
    return ST_DDL_DATE


async def _show_time_step(query, back_cb: str = CB_DDL_STEP_DATE) -> int:
    await _safe_edit(query, get_time_step_text(), get_single_back_keyboard(back_cb))
    return ST_DDL_TIME


async def _show_review(query, context: ContextTypes.DEFAULT_TYPE) -> int:
    due_at = _build_due_at(context)
    await _safe_edit(
        query,
        get_deadline_review_text(
            context.user_data[UD_DDL_SUBJECT_NAME],
            context.user_data[UD_DDL_TITLE],
            due_at,
        ),
        get_deadline_review_keyboard(CB_DDL_STEP_TIME),
    )
    return ST_DDL_REVIEW


async def _show_edit_menu(query) -> int:
    await _safe_edit(query, get_deadline_edit_menu_text(), get_deadline_edit_menu_keyboard(CB_DDL_EDIT_DONE))
    return ST_DDL_EDIT_MENU


async def start_new_subject_deadline(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    _clear_deadline_draft(context)
    return await _show_subject_step(query, CB_DDL_BACK_HUB)


async def start_deadline_for_current_subject(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data.pop(UD_DDL_TITLE, None)
    context.user_data.pop(UD_DDL_DATE, None)
    context.user_data.pop(UD_DDL_TIME, None)
    if not context.user_data.get(UD_DDL_SUBJECT_NAME):
        return await _show_subject_step(query, CB_DDL_BACK_HUB)
    return await _show_title_step(query, context, CB_DDL_BACK_SUBJECT)


async def go_to_subject_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    return await _show_subject_step(query, CB_DDL_BACK_HUB)


async def go_to_title_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    back_cb = CB_DDL_REVIEW_EDIT if context.user_data.get(UD_DDL_EDITING) else None
    return await _show_title_step(query, context, back_cb)


async def go_to_date_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    back_cb = CB_DDL_REVIEW_EDIT if context.user_data.get(UD_DDL_EDITING) else CB_DDL_STEP_TITLE
    return await _show_date_step(query, back_cb)


async def go_to_time_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    back_cb = CB_DDL_REVIEW_EDIT if context.user_data.get(UD_DDL_EDITING) else CB_DDL_STEP_DATE
    return await _show_time_step(query, back_cb)


async def receive_subject_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = (update.message.text or "").strip()
    if not text:
        await update.message.reply_text("Название предмета не должно быть пустым.")
        return ST_DDL_SUBJECT_NAME

    context.user_data[UD_DDL_SUBJECT_ID] = None
    context.user_data[UD_DDL_SUBJECT_NAME] = text
    if context.user_data.get(UD_DDL_EDITING) == "subject":
        context.user_data.pop(UD_DDL_EDITING, None)
        await update.message.reply_text(
            get_deadline_review_text(
                context.user_data[UD_DDL_SUBJECT_NAME],
                context.user_data[UD_DDL_TITLE],
                _build_due_at(context),
            ),
            reply_markup=get_deadline_review_keyboard(CB_DDL_STEP_TIME),
            parse_mode=_HTML,
        )
        return ST_DDL_REVIEW

    await update.message.reply_text(
        get_title_step_text(),
        reply_markup=get_single_back_keyboard(CB_DDL_STEP_SUBJECT),
        parse_mode=_HTML,
    )
    return ST_DDL_TITLE


async def receive_title(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = (update.message.text or "").strip()
    if not text:
        await update.message.reply_text("Название дедлайна не должно быть пустым.")
        return ST_DDL_TITLE

    context.user_data[UD_DDL_TITLE] = text
    if context.user_data.get(UD_DDL_EDITING) == "title":
        context.user_data.pop(UD_DDL_EDITING, None)
        await update.message.reply_text(
            get_deadline_review_text(
                context.user_data[UD_DDL_SUBJECT_NAME],
                context.user_data[UD_DDL_TITLE],
                _build_due_at(context),
            ),
            reply_markup=get_deadline_review_keyboard(CB_DDL_STEP_TIME),
            parse_mode=_HTML,
        )
        return ST_DDL_REVIEW

    await update.message.reply_text(
        get_date_step_text(),
        reply_markup=get_single_back_keyboard(CB_DDL_STEP_TITLE),
        parse_mode=_HTML,
    )
    return ST_DDL_DATE


async def receive_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = (update.message.text or "").strip()
    parsed = _parse_date(text)
    if parsed is None:
        await update.message.reply_text("Неверный формат даты. Используй `ДД.ММ.ГГГГ`.")
        return ST_DDL_DATE
    if parsed < date.today():
        await update.message.reply_text(
            "Нельзя поставить дедлайн раньше сегодняшнего дня.\n"
            "Введи дату еще раз в формате ДД.ММ.ГГГГ."
        )
        return ST_DDL_DATE

    context.user_data[UD_DDL_DATE] = text
    if context.user_data.get(UD_DDL_EDITING) == "date":
        context.user_data.pop(UD_DDL_EDITING, None)
        await update.message.reply_text(
            get_deadline_review_text(
                context.user_data[UD_DDL_SUBJECT_NAME],
                context.user_data[UD_DDL_TITLE],
                _build_due_at(context),
            ),
            reply_markup=get_deadline_review_keyboard(CB_DDL_STEP_TIME),
            parse_mode=_HTML,
        )
        return ST_DDL_REVIEW

    await update.message.reply_text(
        get_time_step_text(),
        reply_markup=get_single_back_keyboard(CB_DDL_STEP_DATE),
        parse_mode=_HTML,
    )
    return ST_DDL_TIME


async def receive_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = (update.message.text or "").strip()
    parsed = _parse_time(text)
    if parsed is None:
        await update.message.reply_text("Неверный формат времени. Используй `ЧЧ:ММ`.")
        return ST_DDL_TIME

    context.user_data[UD_DDL_TIME] = text
    context.user_data.pop(UD_DDL_EDITING, None)
    due_at = _build_due_at(context)
    if _is_past_due(due_at):
        await update.message.reply_text(
            "Нельзя поставить дедлайн в прошлом.\n"
            "Введи время еще раз в формате ЧЧ:ММ."
        )
        return ST_DDL_TIME
    await update.message.reply_text(
        get_deadline_review_text(
            context.user_data[UD_DDL_SUBJECT_NAME],
            context.user_data[UD_DDL_TITLE],
            due_at,
        ),
        reply_markup=get_deadline_review_keyboard(CB_DDL_STEP_TIME),
        parse_mode=_HTML,
    )
    return ST_DDL_REVIEW


async def submit_deadline_review(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    due_at = _build_due_at(context)
    if _is_past_due(due_at):
        await query.answer("Нельзя поставить дедлайн в прошлом.", show_alert=True)
        return ST_DDL_REVIEW
    async with context.bot_data["session_factory"]() as session:
        await create_deadline(
            session,
            user_telegram_id=update.effective_user.id,
            subject_name=context.user_data[UD_DDL_SUBJECT_NAME],
            title=context.user_data[UD_DDL_TITLE],
            due_at=due_at,
            subject_id=context.user_data.get(UD_DDL_SUBJECT_ID),
        )
    await _safe_edit(query, get_deadline_success_text("Готово! Дедлайн успешно добавлен."), get_deadline_success_keyboard())
    _clear_deadline_draft(context)
    return ConversationHandler.END


async def open_edit_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    return await _show_edit_menu(query)


async def finish_edit_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    return await _show_review(query, context)


async def edit_subject_field(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data[UD_DDL_EDITING] = "subject"
    return await _show_subject_step(query, CB_DDL_REVIEW_EDIT)


async def edit_title_field(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data[UD_DDL_EDITING] = "title"
    return await _show_title_step(query, context, CB_DDL_REVIEW_EDIT)


async def edit_date_field(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data[UD_DDL_EDITING] = "date"
    return await _show_date_step(query, CB_DDL_REVIEW_EDIT)


async def edit_time_field(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data[UD_DDL_EDITING] = "time"
    return await _show_time_step(query, CB_DDL_REVIEW_EDIT)


async def start_deadline_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    subject_id = context.user_data.get(UD_DDL_SUBJECT_ID)
    if not subject_id:
        await query.answer("Не удалось определить предмет.", show_alert=True)
        return ConversationHandler.END

    async with context.bot_data["session_factory"]() as session:
        deadlines = await list_subject_deadlines(session, update.effective_user.id, subject_id)
    if not deadlines:
        await query.answer("Здесь пока нет активных дедлайнов.", show_alert=True)
        return ConversationHandler.END

    await query.answer()
    action = query.data
    context.user_data[UD_DDL_ACTION] = action
    action_code = _DEADLINE_ACTION_CODES[action]
    await _safe_edit(
        query,
        get_deadline_action_choice_text(_DEADLINE_ACTION_LABELS[action]),
        get_deadline_action_choice_keyboard(deadlines, action_code),
    )
    return ST_DDL_ACTION_INDEX


async def pick_deadline_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query

    payload = query.data.removeprefix(CB_DDL_ACTION_PICK)
    try:
        action_code, deadline_id_raw = payload.split(":", 1)
        deadline_id = int(deadline_id_raw)
    except ValueError:
        await query.answer("Не удалось определить дедлайн.", show_alert=True)
        return ConversationHandler.END

    action = _DEADLINE_ACTION_BY_CODE.get(action_code)
    if action is None:
        await query.answer("Неизвестное действие.", show_alert=True)
        return ConversationHandler.END

    await query.answer()
    subject_id = context.user_data.get(UD_DDL_SUBJECT_ID)
    async with context.bot_data["session_factory"]() as session:
        result = await session.execute(
            select(Deadline).where(
                Deadline.id == deadline_id,
                Deadline.user_telegram_id == update.effective_user.id,
            )
        )
        deadline = result.scalar_one_or_none()
        if deadline is None or (subject_id and deadline.subject_id != subject_id):
            await query.answer("Дедлайн не найден.", show_alert=True)
            return ConversationHandler.END

        if action == CB_DDL_ACTION_DONE:
            await complete_deadline(session, update.effective_user.id, deadline.id)
            await _safe_edit(
                query,
                get_deadline_success_text(f"«{deadline.title}» отмечен выполненным."),
                get_deadline_success_keyboard(),
            )
            return ConversationHandler.END
        if action == CB_DDL_ACTION_DELETE:
            await remove_deadline(session, update.effective_user.id, deadline.id)
            await _safe_edit(
                query,
                get_deadline_success_text(f"Дедлайн «{deadline.title}» успешно удалён."),
                get_deadline_success_keyboard(),
            )
            return ConversationHandler.END

    context.user_data["ddl_action_deadline_id"] = deadline.id
    context.user_data["ddl_action_deadline_title"] = deadline.title
    if action == CB_DDL_ACTION_MOVE:
        await _safe_edit(
            query,
            get_date_step_text(),
            get_single_back_keyboard(CB_DDL_BACK_SUBJECT),
        )
        return ST_DDL_MOVE_DATE

    await _safe_edit(
        query,
        get_deadline_reminder_choice_text(deadline.title),
        get_deadline_reminder_choice_keyboard(),
    )
    return ST_DDL_REMINDER_PICK


async def receive_move_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = (update.message.text or "").strip()
    parsed_date = _parse_date(text)
    if parsed_date is None:
        await update.message.reply_text("Неверный формат даты. Используй `ДД.ММ.ГГГГ`.")
        return ST_DDL_MOVE_DATE
    if parsed_date < date.today():
        await update.message.reply_text(
            "Нельзя перенести дедлайн раньше сегодняшнего дня.\n"
            "Введи дату еще раз в формате ДД.ММ.ГГГГ."
        )
        return ST_DDL_MOVE_DATE
    context.user_data["ddl_move_date"] = text
    await update.message.reply_text(
        get_time_step_text(),
        reply_markup=get_single_back_keyboard(CB_DDL_BACK_SUBJECT),
        parse_mode=_HTML,
    )
    return ST_DDL_MOVE_TIME


async def receive_move_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = (update.message.text or "").strip()
    parsed_time = _parse_time(text)
    parsed_date = _parse_date(context.user_data.get("ddl_move_date", ""))
    if parsed_time is None or parsed_date is None:
        await update.message.reply_text("Неверный формат времени. Используй `ЧЧ:ММ`.")
        return ST_DDL_MOVE_TIME

    due_at = datetime.combine(parsed_date, parsed_time, tzinfo=timezone.utc)
    if _is_past_due(due_at):
        await update.message.reply_text(
            "Нельзя перенести дедлайн в прошлое.\n"
            "Введи время еще раз в формате ЧЧ:ММ."
        )
        return ST_DDL_MOVE_TIME
    async with context.bot_data["session_factory"]() as session:
        deadline = await reschedule_deadline(
            session,
            update.effective_user.id,
            context.user_data["ddl_action_deadline_id"],
            due_at,
        )
    title = deadline.title if deadline else "Дедлайн"
    await update.message.reply_text(
        get_deadline_success_text(f"«{title}» успешно перенесён."),
        reply_markup=get_deadline_success_keyboard(),
        parse_mode=_HTML,
    )
    return ConversationHandler.END


async def apply_deadline_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    minutes = int(query.data.removeprefix(CB_DDL_REMIND_SET))
    async with context.bot_data["session_factory"]() as session:
        deadline = await set_deadline_reminder(
            session,
            update.effective_user.id,
            context.user_data["ddl_action_deadline_id"],
            minutes,
        )
    title = deadline.title if deadline else "Дедлайн"
    await _safe_edit(query, get_deadline_success_text(f"Напоминание для «{title}» успешно настроено."), get_deadline_success_keyboard())
    return ConversationHandler.END


async def open_custom_deadline_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    title = context.user_data.get("ddl_action_deadline_title", "дедлайна")
    await _safe_edit(
        query,
        get_deadline_custom_reminder_text(title),
        get_single_back_keyboard(CB_DDL_BACK_SUBJECT),
    )
    return ST_DDL_REMINDER_CUSTOM


async def receive_custom_deadline_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = (update.message.text or "").strip()
    minutes = _parse_custom_reminder(text)
    if minutes is None:
        await update.message.reply_text("Напиши время в формате `2д 3ч`, `6ч` или `30м`.")
        return ST_DDL_REMINDER_CUSTOM

    async with context.bot_data["session_factory"]() as session:
        deadline = await set_deadline_reminder(
            session,
            update.effective_user.id,
            context.user_data["ddl_action_deadline_id"],
            minutes,
        )
    title = deadline.title if deadline else "Дедлайн"
    await update.message.reply_text(
        get_deadline_success_text(f"Напоминание для «{title}» успешно настроено."),
        reply_markup=get_deadline_success_keyboard(),
        parse_mode=_HTML,
    )
    return ConversationHandler.END


async def open_deadline_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    async with context.bot_data["session_factory"]() as session:
        settings = await get_deadline_settings(session, update.effective_user.id)
    await _safe_edit(
        query,
        get_deadline_settings_text(settings.reminders_enabled, settings.daily_digest_enabled, settings.daily_digest_time),
        get_deadline_settings_keyboard(),
    )
    return ST_DDL_SETTINGS_MENU


async def open_deadline_setting_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    label = "напоминания" if query.data == CB_DDL_TOGGLE_MAIN else "ежедневные напоминания"
    context.user_data[UD_DDL_SETTINGS_KIND] = query.data
    await _safe_edit(query, get_toggle_choice_text(label), get_toggle_choice_keyboard())
    return ST_DDL_SETTINGS_KIND


async def apply_deadline_setting_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    enabled = query.data == CB_DDL_SET_ON
    kind = context.user_data.get(UD_DDL_SETTINGS_KIND)

    if kind == CB_DDL_TOGGLE_MAIN:
        async with context.bot_data["session_factory"]() as session:
            await save_deadline_settings(session, update.effective_user.id, reminders_enabled=enabled)
        await _safe_edit(
            query,
            get_deadline_success_text(f"Напоминания {'включены' if enabled else 'выключены'}."),
            get_single_back_keyboard(CB_DDL_SETTINGS),
        )
        return ConversationHandler.END

    if not enabled:
        async with context.bot_data["session_factory"]() as session:
            await save_deadline_settings(session, update.effective_user.id, daily_digest_enabled=False)
        await _safe_edit(
            query,
            get_deadline_success_text("Ежедневное напоминание выключено."),
            get_single_back_keyboard(CB_DDL_SETTINGS),
        )
        return ConversationHandler.END

    await _safe_edit(query, get_daily_time_text(), get_single_back_keyboard(CB_DDL_SETTINGS))
    return ST_DDL_SETTINGS_TIME


async def receive_daily_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = (update.message.text or "").strip()
    if _parse_time(text) is None:
        await update.message.reply_text("Неверный формат времени. Используй `ЧЧ:ММ`.")
        return ST_DDL_SETTINGS_TIME
    async with context.bot_data["session_factory"]() as session:
        await save_deadline_settings(
            session,
            update.effective_user.id,
            daily_digest_enabled=True,
            daily_digest_time=text,
        )
    await update.message.reply_text(
        get_deadline_success_text(f"Ежедневное напоминание успешно настроено на {text}."),
        reply_markup=get_single_back_keyboard(CB_DDL_SETTINGS),
        parse_mode=_HTML,
    )
    return ConversationHandler.END


async def save_deadline_settings_screen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await _safe_edit(query, get_deadline_success_text("Настройки напоминаний успешно сохранены."), get_single_back_keyboard(CB_DDL_SETTINGS))
    return ConversationHandler.END


async def show_success_subjects(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    await _render_deadline_subjects(query, context, update.effective_user.id)


async def _scan_deadline_notifications(context: ContextTypes.DEFAULT_TYPE) -> None:
    session_factory = context.bot_data.get("session_factory")
    if session_factory is None:
        return

    now = datetime.now(timezone.utc)
    current_hhmm = now.strftime("%H:%M")
    today = now.date()

    try:
        async with session_factory() as session:
            reminders = await get_due_deadline_reminders(session, now)
            for deadline, _settings, subject_name in reminders:
                await context.bot.send_message(
                    chat_id=deadline.user_telegram_id,
                    text=get_deadline_reminder_message(subject_name, deadline.title, deadline.due_at),
                    reply_markup=get_deadline_notification_keyboard(),
                    parse_mode=_HTML,
                )
                await mark_deadline_reminder_sent(session, deadline.id)

            digests = await get_due_daily_digests(session, current_hhmm, today)
            for settings in digests:
                upcoming = await get_upcoming_deadlines(session, settings.user_telegram_id, days_ahead=7)
                user_result = await session.execute(select(User).where(User.telegram_id == settings.user_telegram_id))
                user = user_result.scalar_one_or_none()
                owner_name = (user.first_name if user and user.first_name else "студента")
                await context.bot.send_message(
                    chat_id=settings.user_telegram_id,
                    text=get_daily_digest_text(upcoming, settings.daily_digest_time),
                    reply_markup=get_deadline_notification_keyboard(),
                    parse_mode=_HTML,
                    disable_notification=True,
                )
                await mark_daily_digest_sent(session, settings.user_telegram_id, today)
    except Exception:
        logger.exception("Ошибка фоновой проверки дедлайнов")


def setup_deadline_jobs(app: Application) -> None:
    if app.job_queue is None:
        return
    if app.job_queue.get_jobs_by_name("deadline_notifications_scan"):
        return
    app.job_queue.run_repeating(
        _scan_deadline_notifications,
        interval=60,
        first=15,
        name="deadline_notifications_scan",
    )


def register(app: Application) -> None:
    create_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(start_new_subject_deadline, pattern=rf"^{re.escape(CB_DDL_NEW_SUBJECT)}$"),
            CallbackQueryHandler(start_deadline_for_current_subject, pattern=rf"^{re.escape(CB_DDL_CREATE)}$"),
        ],
        states={
            ST_DDL_SUBJECT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_subject_name)],
            ST_DDL_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_title)],
            ST_DDL_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_date)],
            ST_DDL_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_time)],
            ST_DDL_REVIEW: [
                CallbackQueryHandler(submit_deadline_review, pattern=rf"^{re.escape(CB_DDL_REVIEW_CREATE)}$"),
                CallbackQueryHandler(open_edit_menu, pattern=rf"^{re.escape(CB_DDL_REVIEW_EDIT)}$"),
            ],
            ST_DDL_EDIT_MENU: [
                CallbackQueryHandler(edit_subject_field, pattern=rf"^{re.escape(CB_DDL_EDIT_SUBJECT)}$"),
                CallbackQueryHandler(edit_title_field, pattern=rf"^{re.escape(CB_DDL_EDIT_TITLE)}$"),
                CallbackQueryHandler(edit_date_field, pattern=rf"^{re.escape(CB_DDL_EDIT_DATE)}$"),
                CallbackQueryHandler(edit_time_field, pattern=rf"^{re.escape(CB_DDL_EDIT_TIME)}$"),
                CallbackQueryHandler(finish_edit_menu, pattern=rf"^{re.escape(CB_DDL_EDIT_DONE)}$"),
            ],
        },
        fallbacks=[
            CallbackQueryHandler(go_to_subject_step, pattern=rf"^{re.escape(CB_DDL_STEP_SUBJECT)}$"),
            CallbackQueryHandler(go_to_title_step, pattern=rf"^{re.escape(CB_DDL_STEP_TITLE)}$"),
            CallbackQueryHandler(go_to_date_step, pattern=rf"^{re.escape(CB_DDL_STEP_DATE)}$"),
            CallbackQueryHandler(go_to_time_step, pattern=rf"^{re.escape(CB_DDL_STEP_TIME)}$"),
            CallbackQueryHandler(open_edit_menu, pattern=rf"^{re.escape(CB_DDL_REVIEW_EDIT)}$"),
            CallbackQueryHandler(back_to_deadlines_hub, pattern=rf"^{re.escape(CB_DDL_BACK_HUB)}$"),
            CallbackQueryHandler(back_to_subject_deadlines, pattern=rf"^{re.escape(CB_DDL_BACK_SUBJECT)}$"),
            CallbackQueryHandler(go_to_main_from_deadlines, pattern=rf"^{re.escape(CB_NAV_MAIN)}$"),
        ],
        per_message=False,
    )

    action_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(start_deadline_action, pattern=rf"^({re.escape(CB_DDL_ACTION_DONE)}|{re.escape(CB_DDL_ACTION_MOVE)}|{re.escape(CB_DDL_ACTION_DELETE)}|{re.escape(CB_DDL_ACTION_REMIND)})$")
        ],
        states={
            ST_DDL_ACTION_INDEX: [CallbackQueryHandler(pick_deadline_action, pattern=rf"^{re.escape(CB_DDL_ACTION_PICK)}")],
            ST_DDL_MOVE_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_move_date)],
            ST_DDL_MOVE_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_move_time)],
            ST_DDL_REMINDER_PICK: [
                CallbackQueryHandler(apply_deadline_reminder, pattern=rf"^{re.escape(CB_DDL_REMIND_SET)}"),
                CallbackQueryHandler(open_custom_deadline_reminder, pattern=rf"^{re.escape(CB_DDL_REMIND_CUSTOM)}$"),
            ],
            ST_DDL_REMINDER_CUSTOM: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_custom_deadline_reminder)],
        },
        fallbacks=[
            CallbackQueryHandler(back_to_subject_deadlines, pattern=rf"^{re.escape(CB_DDL_BACK_SUBJECT)}$"),
            CallbackQueryHandler(go_to_main_from_deadlines, pattern=rf"^{re.escape(CB_NAV_MAIN)}$"),
        ],
        per_message=False,
    )

    settings_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(open_deadline_settings, pattern=rf"^{re.escape(CB_DDL_SETTINGS)}$")],
        states={
            ST_DDL_SETTINGS_MENU: [
                CallbackQueryHandler(open_deadline_setting_choice, pattern=rf"^({re.escape(CB_DDL_TOGGLE_MAIN)}|{re.escape(CB_DDL_TOGGLE_DAILY)})$"),
                CallbackQueryHandler(save_deadline_settings_screen, pattern=rf"^{re.escape(CB_DDL_SETTINGS_SAVE)}$"),
            ],
            ST_DDL_SETTINGS_KIND: [
                CallbackQueryHandler(apply_deadline_setting_choice, pattern=rf"^({re.escape(CB_DDL_SET_ON)}|{re.escape(CB_DDL_SET_OFF)})$")
            ],
            ST_DDL_SETTINGS_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_daily_time)],
        },
        fallbacks=[
            CallbackQueryHandler(open_deadline_settings, pattern=rf"^{re.escape(CB_DDL_SETTINGS)}$"),
            CallbackQueryHandler(back_to_deadlines_hub, pattern=rf"^{re.escape(CB_DDL_BACK_HUB)}$"),
            CallbackQueryHandler(go_to_main_from_deadlines, pattern=rf"^{re.escape(CB_NAV_MAIN)}$"),
        ],
        per_message=False,
    )

    app.add_handler(create_conv)
    app.add_handler(action_conv)
    app.add_handler(settings_conv)

    mapping = [
        (CB_MAIN_DEADLINES, open_deadlines_hub),
        (CB_DDL_SUBJECTS, open_deadline_subjects),
        (CB_DDL_SUCCESS_SUBS, show_success_subjects),
        (CB_DDL_BACK_HUB, open_deadlines_hub),
        (CB_DDL_BACK_SUBJECTS, open_deadline_subjects),
    ]
    for cb, handler in mapping:
        app.add_handler(CallbackQueryHandler(handler, pattern=rf"^{re.escape(cb)}$"))

    app.add_handler(CallbackQueryHandler(open_subject_deadlines, pattern=rf"^{re.escape(CB_DDL_SUBJECT)}\d+$"))
    setup_deadline_jobs(app)
