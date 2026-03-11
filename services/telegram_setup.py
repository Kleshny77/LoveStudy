from telegram import InlineKeyboardMarkup

from constants import (
    CB_MAIN_DEADLINES,
    CB_MAIN_PROFILE,
)
from services.ui import BUTTON_PRIMARY, em, ib


def get_help_text() -> str:
    return em(
        "👋 <b>LoveStudy</b>\n\n"
        "Быстрые команды:\n"
        "/menu — главное меню\n"
        "/profile — профиль и статистика\n"
        "/materials — материалы и предметы\n"
        "/focus — помодоро\n"
        "/deadlines — дедлайны\n"
        "/friends — друзья и рейтинг\n"
        "/today — краткая сводка на сегодня"
    )


def get_group_redirect_text(bot_username: str | None) -> str:
    link = f"https://t.me/{bot_username}" if bot_username else None
    text = em(
        "👋 Этот сценарий удобнее использовать в личке с ботом.\n\n"
        "Открой бота в личных сообщениях, и там будут доступны материалы, дедлайны, фокус и профиль."
    )
    if link:
        text += f"\n\n<a href=\"{link}\">Открыть бота</a>"
    return text


def get_group_redirect_keyboard(bot_username: str | None) -> InlineKeyboardMarkup | None:
    if not bot_username:
        return None
    return InlineKeyboardMarkup([
        [ib("👤 Открыть бота", url=f"https://t.me/{bot_username}", style=BUTTON_PRIMARY)],
    ])


def get_today_text(
    upcoming_lines: list[str],
    focus_sessions_total: int,
    materials_total: int,
    subjects_total: int,
) -> str:
    deadlines_block = "\n".join(upcoming_lines) if upcoming_lines else "На ближайшие 3 дня срочных дедлайнов нет."
    return em(
        "📊 <b>Краткая сводка</b>\n\n"
        f"📚 Предметов: {subjects_total}\n"
        f"📎 Материалов: {materials_total}\n"
        f"🔥 Завершённых фокус-сессий: {focus_sessions_total}\n\n"
        "⏰ Ближайшие дедлайны:\n"
        f"{deadlines_block}"
    )


def get_today_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [ib("⏰ Открыть дедлайны", callback_data=CB_MAIN_DEADLINES, style=BUTTON_PRIMARY)],
        [ib("📊 Открыть профиль", callback_data=CB_MAIN_PROFILE)],
    ])


def get_deadline_notification_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [ib("⏰ К дедлайнам", callback_data=CB_MAIN_DEADLINES, style=BUTTON_PRIMARY)],
    ])


