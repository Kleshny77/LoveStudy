from datetime import datetime

from telegram import InlineKeyboardMarkup

from constants import (
    CB_DDL_ACTION_DELETE,
    CB_DDL_ACTION_DONE,
    CB_DDL_ACTION_MOVE,
    CB_DDL_ACTION_PICK,
    CB_DDL_ACTION_REMIND,
    CB_DDL_BACK_HUB,
    CB_DDL_BACK_SUBJECT,
    CB_DDL_BACK_SUBJECTS,
    CB_DDL_EDIT_DATE,
    CB_DDL_EDIT_DONE,
    CB_DDL_EDIT_SUBJECT,
    CB_DDL_EDIT_TIME,
    CB_DDL_EDIT_TITLE,
    CB_DDL_CREATE,
    CB_DDL_NEW_SUBJECT,
    CB_DDL_REMIND_CUSTOM,
    CB_DDL_REMIND_SET,
    CB_DDL_REVIEW_CREATE,
    CB_DDL_REVIEW_EDIT,
    CB_DDL_SETTINGS,
    CB_DDL_SETTINGS_SAVE,
    CB_DDL_SET_OFF,
    CB_DDL_SET_ON,
    CB_DDL_SUBJECT,
    CB_DDL_SUBJECTS,
    CB_DDL_SUCCESS_SUBS,
    CB_DDL_TOGGLE_DAILY,
    CB_DDL_TOGGLE_MAIN,
    CB_NAV_MAIN,
)
from services.ui import BUTTON_DANGER, BUTTON_PRIMARY, BUTTON_SUCCESS, em, ib


def _format_due(due_at: datetime) -> str:
    return due_at.strftime("%d.%m.%Y %H:%M")


def get_deadlines_hub_text(active_items: list[tuple[object, str]]) -> str:
    if not active_items:
        return em("⏰ <b>У тебя нет дедлайнов.</b>\n\nДобавить?")

    lines = [
        f"{idx}. {subject_name} — {deadline.title}: {_format_due(deadline.due_at)}"
        for idx, (deadline, subject_name) in enumerate(active_items, start=1)
    ]
    return em(
        (
        "⏰ <b>Твои активные дедлайны</b>\n\n"
        + "\n".join(lines)
        + "\n\nДобавить?"
        )
    )


def get_deadlines_hub_keyboard(subjects: list[tuple[int, str]]) -> InlineKeyboardMarkup:
    rows: list[list[object]] = []
    for i in range(0, min(len(subjects), 4), 2):
        pair = subjects[i:i + 2]
        rows.append([
            ib(name, callback_data=f"{CB_DDL_SUBJECT}{subject_id}")
            for subject_id, name in pair
        ])
    if len(subjects) > 4:
        rows.append([ib("📚 Мои предметы", callback_data=CB_DDL_SUBJECTS)])
    rows.append([ib("➕ Новый предмет", callback_data=CB_DDL_NEW_SUBJECT, style=BUTTON_SUCCESS)])
    rows.append([ib("🔔 Настройки напоминаний", callback_data=CB_DDL_SETTINGS, style=BUTTON_PRIMARY)])
    rows.append([ib("🏠 Главное меню", callback_data=CB_NAV_MAIN)])
    return InlineKeyboardMarkup(rows)


def get_deadline_subjects_text(subjects: list[tuple[int, str]]) -> str:
    if not subjects:
        return em("📚 <b>У тебя пока нет предметов.</b>\n\nСначала создай новый предмет для дедлайна.")
    return em("📚 <b>Ваши предметы</b>\n\nВыбери предмет, чтобы посмотреть дедлайны.")


def get_deadline_subjects_keyboard(subjects: list[tuple[int, str]]) -> InlineKeyboardMarkup:
    rows: list[list[object]] = []
    for i in range(0, len(subjects), 2):
        pair = subjects[i:i + 2]
        rows.append([
            ib(name, callback_data=f"{CB_DDL_SUBJECT}{subject_id}")
            for subject_id, name in pair
        ])
    rows.append([
        ib("🔙 Назад", callback_data=CB_DDL_BACK_HUB),
        ib("🏠 Главное меню", callback_data=CB_NAV_MAIN),
    ])
    return InlineKeyboardMarkup(rows)


def get_subject_deadlines_text(subject_name: str, deadlines: list[object]) -> str:
    if not deadlines:
        return em(
            (
            f"⏰ <b>Дедлайны по «{subject_name}»</b>\n\n"
            "Пока здесь нет активных дедлайнов."
            )
        )

    lines = [f"{idx}. {deadline.title} — {_format_due(deadline.due_at)}" for idx, deadline in enumerate(deadlines, start=1)]
    return em(f"⏰ <b>Дедлайны по «{subject_name}»</b>\n\n" + "\n".join(lines))


def get_subject_deadlines_keyboard(has_deadlines: bool = True) -> InlineKeyboardMarkup:
    rows = [[ib("➕ Новый дедлайн", callback_data=CB_DDL_CREATE, style=BUTTON_SUCCESS)]]
    if has_deadlines:
        rows.extend([
            [
                ib("🔔 Напоминания", callback_data=CB_DDL_ACTION_REMIND),
                ib("📅 Перенести", callback_data=CB_DDL_ACTION_MOVE, style=BUTTON_PRIMARY),
            ],
            [
                ib("🗑 Удалить", callback_data=CB_DDL_ACTION_DELETE, style=BUTTON_DANGER),
                ib("✅ Выполнено", callback_data=CB_DDL_ACTION_DONE, style=BUTTON_SUCCESS),
            ],
        ])
    rows.append([
        ib("🔙 Назад", callback_data=CB_DDL_BACK_SUBJECTS),
        ib("🏠 Главное меню", callback_data=CB_NAV_MAIN),
    ])
    return InlineKeyboardMarkup(rows)


def get_subject_step_text() -> str:
    return em("✍️ Напиши название предмета")


def get_title_step_text() -> str:
    return em("✍️ Напиши название дедлайна")


def get_date_step_text() -> str:
    return em("📅 Когда дедлайн?\n\n<i>Напиши в формате ДД.ММ.ГГГГ</i>")


def get_time_step_text() -> str:
    return em("⏰ Во сколько дедлайн?\n\n<i>Напиши в формате ЧЧ:ММ</i>")


def get_single_back_keyboard(back_cb: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            ib("🔙 Назад", callback_data=back_cb),
            ib("🏠 Главное меню", callback_data=CB_NAV_MAIN),
        ],
    ])


def get_deadline_review_text(subject_name: str, title: str, due_at: datetime) -> str:
    return em(
        (
        "📝 <b>Проверь дедлайн</b>\n\n"
        f"Предмет: {subject_name}\n"
        f"Название: {title}\n"
        f"Дата: {due_at.strftime('%d.%m.%Y')}\n"
        f"Время: {due_at.strftime('%H:%M')}"
        )
    )


def get_deadline_review_keyboard(back_cb: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            ib("✅ Создать", callback_data=CB_DDL_REVIEW_CREATE, style=BUTTON_SUCCESS),
            ib("✏️ Изменить", callback_data=CB_DDL_REVIEW_EDIT, style=BUTTON_PRIMARY),
        ],
        [
            ib("🔙 Назад", callback_data=back_cb),
            ib("🏠 Главное меню", callback_data=CB_NAV_MAIN),
        ],
    ])


def get_deadline_edit_menu_text() -> str:
    return "Что хочешь изменить?"


def get_deadline_edit_menu_keyboard(back_cb: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            ib("Предмет", callback_data=CB_DDL_EDIT_SUBJECT),
            ib("Название", callback_data=CB_DDL_EDIT_TITLE),
        ],
        [
            ib("Дата", callback_data=CB_DDL_EDIT_DATE),
            ib("Время", callback_data=CB_DDL_EDIT_TIME),
        ],
        [ib("✅ Готово!", callback_data=CB_DDL_EDIT_DONE, style=BUTTON_SUCCESS)],
        [
            ib("🔙 Назад", callback_data=back_cb),
            ib("🏠 Главное меню", callback_data=CB_NAV_MAIN),
        ],
    ])


def get_deadline_action_prompt_text(action_label: str) -> str:
    return em(f"✍️ Напиши цифру для действия «{action_label}»")


def get_deadline_action_prompt_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            ib("🔙 Назад", callback_data=CB_DDL_BACK_SUBJECT),
            ib("🏠 Главное меню", callback_data=CB_NAV_MAIN),
        ],
    ])


def get_deadline_action_choice_text(action_label: str) -> str:
    return em(f"Выбери дедлайн для действия «{action_label}».")


def get_deadline_action_choice_keyboard(deadlines: list[object], action_code: str) -> InlineKeyboardMarkup:
    rows = [
        [ib(f"{idx}. {deadline.title}", callback_data=f"{CB_DDL_ACTION_PICK}{action_code}:{deadline.id}")]
        for idx, deadline in enumerate(deadlines, start=1)
    ]
    rows.append([
        ib("🔙 Назад", callback_data=CB_DDL_BACK_SUBJECT),
        ib("🏠 Главное меню", callback_data=CB_NAV_MAIN),
    ])
    return InlineKeyboardMarkup(rows)


def get_deadline_reminder_choice_text(deadline_title: str) -> str:
    return em(f"🔔 Выбери время для напоминания о «{deadline_title}»")


def get_deadline_reminder_choice_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            ib("За 3 часа", callback_data=f"{CB_DDL_REMIND_SET}{3 * 60}"),
            ib("За 1 день", callback_data=f"{CB_DDL_REMIND_SET}{24 * 60}"),
        ],
        [
            ib("⚙️ Свое время", callback_data=CB_DDL_REMIND_CUSTOM, style=BUTTON_PRIMARY),
        ],
        [
            ib("🔙 Назад", callback_data=CB_DDL_BACK_SUBJECT),
            ib("🏠 Главное меню", callback_data=CB_NAV_MAIN),
        ],
    ])


def get_deadline_custom_reminder_text(deadline_title: str) -> str:
    return em(
        "⚙️ Настрой свое время напоминания\n\n"
        f"Для дедлайна «{deadline_title}» напиши за сколько предупредить.\n"
        "Примеры: <code>2д 3ч</code>, <code>6ч</code>, <code>30м</code>"
    )


def get_deadline_settings_text(reminders_enabled: bool, daily_enabled: bool, daily_time: str) -> str:
    main_label = "Вкл" if reminders_enabled else "Выкл"
    daily_label = f"Вкл, {daily_time}" if daily_enabled else "Выкл"
    return em(
        (
        "🔔 <b>Настройки напоминаний</b>\n\n"
        f"🔔 Напоминания: {main_label}\n"
        "⏱ Быстрые варианты: за 3 часа, за 1 день или свое время\n"
        f"🗓 Ежедневно (если дедлайн ≤ 7 дней): {daily_label}"
        )
    )


def get_deadline_settings_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            ib("🔔 Вкл / Выкл", callback_data=CB_DDL_TOGGLE_MAIN),
            ib("🗓 Ежедневно", callback_data=CB_DDL_TOGGLE_DAILY),
        ],
        [ib("✅ Сохранить", callback_data=CB_DDL_SETTINGS_SAVE, style=BUTTON_SUCCESS)],
        [
            ib("🔙 Назад", callback_data=CB_DDL_BACK_HUB),
            ib("🏠 Главное меню", callback_data=CB_NAV_MAIN),
        ],
    ])


def get_toggle_choice_text(label: str) -> str:
    return f"Как хочешь настраивать «{label}»?"


def get_toggle_choice_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            ib("Вкл", callback_data=CB_DDL_SET_ON, style=BUTTON_SUCCESS),
            ib("Выкл", callback_data=CB_DDL_SET_OFF, style=BUTTON_DANGER),
        ],
        [
            ib("🔙 Назад", callback_data=CB_DDL_SETTINGS),
            ib("🏠 Главное меню", callback_data=CB_NAV_MAIN),
        ],
    ])


def get_daily_time_text() -> str:
    return em("Во сколько хотите настроить ежедневное напоминание?\n\n<i>Напиши в формате ЧЧ:ММ</i>")


def get_deadline_success_text(text: str) -> str:
    return em(f"✅ {text}")


def get_deadline_success_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            ib("📚 Мои предметы", callback_data=CB_DDL_SUCCESS_SUBS, style=BUTTON_PRIMARY),
            ib("🏠 Главное меню", callback_data=CB_NAV_MAIN),
        ],
    ])


def get_deadline_reminder_message(subject_name: str, deadline_title: str, due_at: datetime) -> str:
    return em(
        (
        "🔔 <b>Напоминание о дедлайне</b>\n\n"
        f"Предмет: {subject_name}\n"
        f"Дедлайн: {deadline_title}\n"
        f"Срок: {_format_due(due_at)}"
        )
    )


def get_daily_digest_text(items: list[tuple[object, str]], daily_time: str) -> str:
    if not items:
        return em(
            (
            "🗓 <b>Ежедневное напоминание</b>\n\n"
            f"На {daily_time} срочных дедлайнов на ближайшие 7 дней нет."
            )
        )
    lines = [
        f"{idx}. {subject_name} — {deadline.title}: {_format_due(deadline.due_at)}"
        for idx, (deadline, subject_name) in enumerate(items, start=1)
    ]
    return em(
        (
        "🗓 <b>Ежедневное напоминание</b>\n\n"
        "Дедлайны на ближайшие 7 дней:\n"
        + "\n".join(lines)
        )
    )
