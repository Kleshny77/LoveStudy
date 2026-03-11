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
        "/today — краткая сводка на сегодня\n"
        "/terms — условия подписки и оплаты\n"
        "/paysupport — помощь по оплате"
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


def get_terms_text(price_stars: int, support_contact: str | None) -> str:
    support_line = (
        f"По вопросам оплаты и спорным ситуациям: {support_contact}"
        if support_contact
        else "По вопросам оплаты и спорным ситуациям используй команду /paysupport."
    )
    return em(
        "📄 <b>Условия LoveStudy Pro</b>\n\n"
        f"1. LoveStudy Pro стоит {price_stars} Stars за 30 дней.\n"
        "2. Подписка оформляется внутри Telegram и может продлеваться автоматически.\n"
        "3. Pro снимает лимит на генерацию тестов и дает безграничную генерацию, пока подписка активна.\n"
        "4. Если автопродление отключено, доступ Pro сохраняется до конца уже оплаченного периода.\n"
        "5. Возвраты и спорные случаи рассматриваются отдельно после обращения в поддержку.\n"
        "6. Используя оплату, пользователь соглашается с этими условиями.\n\n"
        f"{support_line}"
    )


def get_paysupport_text(support_contact: str | None) -> str:
    contact_line = (
        f"Связаться с поддержкой: {support_contact}"
        if support_contact
        else "Контакт поддержки не настроен. Добавь `PAY_SUPPORT_CONTACT` в `.env`, чтобы команда вела на нужный контакт."
    )
    return em(
        "💳 <b>Поддержка по оплате</b>\n\n"
        "Если есть проблема с оплатой, продлением или доступом к LoveStudy Pro, напиши в поддержку и приложи:\n"
        "• свой Telegram username\n"
        "• примерное время платежа\n"
        "• описание проблемы\n\n"
        f"{contact_line}"
    )


