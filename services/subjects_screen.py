# экран «Мои предметы»

from telegram import InlineKeyboardMarkup

from constants import CB_MAIN_UPLOAD, CB_NAV_HUB, CB_NAV_MAIN
from services.ui import BUTTON_PRIMARY, em, ib


def get_subjects_screen_text() -> str:
    return em("Твои предметы и материалы.\nМожешь загрузить новый файл или посмотреть список.")


def get_subjects_screen_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [ib("📤 Загрузить материалы", callback_data=CB_MAIN_UPLOAD, style=BUTTON_PRIMARY, skip_custom_emoji=True)],
        [
            ib("🔙 Назад", callback_data=CB_NAV_HUB),
            ib("🏠 Главное меню", callback_data=CB_NAV_MAIN),
        ],
    ])
