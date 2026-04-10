# текст и кнопки главного экрана; HTML-режим, без Markdown

from telegram import InlineKeyboardMarkup

from constants import (
    CB_MAIN_DEADLINES,
    CB_MAIN_MATERIALS,
    CB_MAIN_PROFILE,
    CB_MAIN_SUBJECTS,
    CB_MAIN_UPLOAD,
    CB_NAV_MAIN,
)
from services.ui import BUTTON_PRIMARY, em, ib


def get_main_menu_text(user_name: str | None = None) -> str:
    name = user_name or "друг"
    return em(
        (
        f"Привет, {name}! 👋\n\n"
        "Добро пожаловать в бот-помощник для студентов! "
        "Он поможет держать учёбу под контролем и меньше стрессовать :)\n\n"
        "<b>Здесь ты можешь:</b>\n"
        "• Хранить все материалы в одном месте\n"
        "• Готовиться к экзаменам с помощью тестов\n"
        "• Запускать таймер помодоро\n"
        "• Добавлять дедлайны и получать напоминания\n"
        "• Соревноваться с друзьями\n\n"
        "Выбери раздел ниже и начнём 👇"
        )
    )


def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [ib("👤 Профиль", callback_data=CB_MAIN_PROFILE)],
        [ib("📚 Мои предметы", callback_data=CB_MAIN_MATERIALS)],
        [ib("⏰ Дедлайны", callback_data=CB_MAIN_DEADLINES, style=BUTTON_PRIMARY)],
        [ib("🏆 Друзья и рейтинг", callback_data="main:friends", style=BUTTON_PRIMARY)],
        [ib("🍅 Помодоро", callback_data="main:pomodoro", style=BUTTON_PRIMARY)],
    ])


def get_materials_hub_text() -> str:
    return em("💖 <b>Мои предметы</b>\n\nЧто хочешь сделать?")


def get_materials_hub_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [ib("📤 Загрузить материалы", callback_data=CB_MAIN_UPLOAD, style=BUTTON_PRIMARY, skip_custom_emoji=True)],
        [ib("📂 Просмотр предметов и материалов", callback_data=CB_MAIN_SUBJECTS)],
        [ib("🔙 Назад", callback_data=CB_NAV_MAIN)],
    ])
