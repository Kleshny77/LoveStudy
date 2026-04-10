# Тексты и клавиатуры для помодоро-экранов

from telegram import InlineKeyboardMarkup

from constants import (
    CB_NAV_MAIN,
    CB_POMO_AUT_OFF, CB_POMO_AUT_ON,
    CB_POMO_AUTO, CB_POMO_CFG, CB_POMO_CUSTOM,
    CB_POMO_NEXT, CB_POMO_NOTIF, CB_POMO_OPEN,
    CB_POMO_PAUSE, CB_POMO_PRESET,
    CB_POMO_REM_OFF, CB_POMO_REM_ON, CB_POMO_REMIND,
    CB_POMO_RESUME, CB_POMO_SKIP, CB_POMO_START, CB_POMO_STOP,
)
from services.ui import BUTTON_DANGER, BUTTON_PRIMARY, BUTTON_SUCCESS, em, ib


def _fmt(seconds: int) -> str:
    m, s = divmod(max(0, seconds), 60)
    return f"{m:02d}:{s:02d}"


# ──────────────────────────────────────────────
# Главный экран (фокус-меню)
# ──────────────────────────────────────────────

def get_focus_menu_text(work_min: int, break_min: int, sessions_today: int) -> str:
    return em(
        (
        f"🍅 <b>Режим фокуса</b>\n\n"
        f"Рабочий интервал: {work_min} минут\n"
        f"Перерыв: {break_min} минут\n"
        f"Сегодня завершено: {sessions_today} сессий\n\n"
        "Готов начать?"
        )
    )


def get_focus_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [ib("▶ Начать фокус", callback_data=CB_POMO_START, style=BUTTON_SUCCESS)],
        [ib("⚙ Настроить интервалы", callback_data=CB_POMO_CFG)],
        [ib("🔔 Настройки уведомлений", callback_data=CB_POMO_NOTIF, style=BUTTON_PRIMARY)],
        [ib("🔙 Назад", callback_data=CB_NAV_MAIN)],
    ])


# ──────────────────────────────────────────────
# Активный рабочий таймер
# ──────────────────────────────────────────────

def get_work_timer_text(remaining: int) -> str:
    return em(
        (
        f"🍅 <b>Фокус начался</b>\n"
        f"Осталось: {_fmt(remaining)}\n\n"
        "Не отвлекайся. Ты в режиме концентрации 🔥"
        )
    )


def get_work_timer_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [ib("⏸ Пауза", callback_data=CB_POMO_PAUSE, style=BUTTON_PRIMARY)],
        [ib("❌ Завершить", callback_data=CB_POMO_STOP, style=BUTTON_DANGER)],
    ])


# ──────────────────────────────────────────────
# Пауза
# ──────────────────────────────────────────────

def get_paused_text(remaining: int) -> str:
    return em(
        (
        f"⏸ <b>Пауза</b>\n"
        f"Осталось: {_fmt(remaining)}\n\n"
        "Таймер на паузе."
        )
    )


def get_paused_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [ib("▶ Продолжить", callback_data=CB_POMO_RESUME, style=BUTTON_SUCCESS, skip_custom_emoji=True)],
        [ib("❌ Завершить", callback_data=CB_POMO_STOP, style=BUTTON_DANGER)],
    ])


# ──────────────────────────────────────────────
# Переход к перерыву (отправляется как сообщение)
# ──────────────────────────────────────────────

def get_work_done_text(work_min: int, break_min: int) -> str:
    return em(
        (
        f"✅ <b>{work_min} минут завершены!</b>\n\n"
        f"Время отдыха — {break_min} минут ☕"
        )
    )


# ──────────────────────────────────────────────
# Активный таймер перерыва
# ──────────────────────────────────────────────

def get_break_timer_text(remaining: int) -> str:
    return em(
        (
        f"☕ <b>Перерыв</b>\n"
        f"Осталось: {_fmt(remaining)}"
        )
    )


def get_break_timer_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [ib("▶ Пропустить отдых", callback_data=CB_POMO_SKIP, style=BUTTON_PRIMARY)],
        [ib("❌ Завершить цикл", callback_data=CB_POMO_STOP, style=BUTTON_DANGER)],
    ])


# ──────────────────────────────────────────────
# Цикл завершён
# ──────────────────────────────────────────────

def get_cycle_done_text(sessions_today: int) -> str:
    return em(
        (
        f"🎉 <b>Цикл завершён!</b>\n"
        f"+1 помодоро-сессия\n\n"
        f"Всего сегодня: {sessions_today} 🍅\n\n"
        "Хочешь ещё один?"
        )
    )


def get_cycle_done_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [ib("🔄 Начать следующий цикл", callback_data=CB_POMO_NEXT, style=BUTTON_SUCCESS)],
        [
            ib("🔙 Назад", callback_data=CB_POMO_OPEN),
            ib("🏠 Главное меню", callback_data=CB_NAV_MAIN),
        ],
    ])


# ──────────────────────────────────────────────
# Настройка интервалов
# ──────────────────────────────────────────────

def get_interval_cfg_text() -> str:
    return em("⚙ <b>Настройка таймера</b>\nВыбери длительность работы и отдыха.")


def get_interval_cfg_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [ib("🍅 25 / 5", callback_data=f"{CB_POMO_PRESET}25:5")],
        [ib("🍅 45 / 10", callback_data=f"{CB_POMO_PRESET}45:10")],
        [ib("🍅 50 / 10", callback_data=f"{CB_POMO_PRESET}50:10")],
        [ib("Ручная настройка", callback_data=CB_POMO_CUSTOM, style=BUTTON_PRIMARY)],
        [ib("🔙 Назад", callback_data=CB_POMO_OPEN), ib("🏠 Главное меню", callback_data=CB_NAV_MAIN)],
    ])


# ──────────────────────────────────────────────
# Ручной ввод интервала
# ──────────────────────────────────────────────

def get_custom_input_text() -> str:
    return em(
        (
        "Пришли свою длительность сессии в формате:\n"
        "<b>(время работы) / (время отдыха)</b>\n\n"
        "Только цифры через /\n"
        "<i>Например: 40/15</i>"
        )
    )


def get_custom_input_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [ib("🔙 Назад", callback_data=CB_POMO_CFG), ib("🏠 Главное меню", callback_data=CB_NAV_MAIN)],
    ])


# ──────────────────────────────────────────────
# Настройки уведомлений
# ──────────────────────────────────────────────

def get_notif_settings_text(reminder: bool, auto_break: bool) -> str:
    r = "Вкл" if reminder else "Выкл"
    a = "Да"  if auto_break else "Нет"
    return em(
        (
        f"📳 Напоминание за 1 минуту до конца: {r}\n"
        f"🔄 Автоматически запускать перерыв: {a}"
        )
    )


def get_notif_settings_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [ib("Настроить 📳 Напоминание", callback_data=CB_POMO_REMIND, style=BUTTON_PRIMARY)],
        [ib("Настроить 🔄 Автозапуск", callback_data=CB_POMO_AUTO)],
        [ib("🔙 Назад", callback_data=CB_POMO_OPEN), ib("🏠 Главное меню", callback_data=CB_NAV_MAIN)],
    ])


def get_reminder_toggle_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            ib("вкл", callback_data=CB_POMO_REM_ON, style=BUTTON_SUCCESS),
            ib("выкл", callback_data=CB_POMO_REM_OFF, style=BUTTON_DANGER),
        ],
        [ib("🔙 Назад", callback_data=CB_POMO_NOTIF), ib("🏠 Главное меню", callback_data=CB_NAV_MAIN)],
    ])


def get_auto_toggle_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            ib("да", callback_data=CB_POMO_AUT_ON, style=BUTTON_SUCCESS),
            ib("нет", callback_data=CB_POMO_AUT_OFF, style=BUTTON_DANGER),
        ],
        [ib("🔙 Назад", callback_data=CB_POMO_NOTIF), ib("🏠 Главное меню", callback_data=CB_NAV_MAIN)],
    ])
