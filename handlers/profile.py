import re

from telegram import LabeledPrice, Update
from telegram.constants import ParseMode
from telegram.error import BadRequest
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    PreCheckoutQueryHandler,
    filters,
)

from config import get_subscription_price_stars
from constants import (
    CB_MAIN_PROFILE,
    CB_PROF_ACHIEV,
    CB_PROF_ACTIVITY,
    CB_PROF_DEADLINES,
    CB_PROF_MATERIALS,
    CB_PROF_PERIOD,
    CB_PROF_PERIOD_SET,
    CB_PROF_SUBSCRIPTION,
    CB_PROF_SUB_BUY,
    CB_PROF_SUB_MANAGE,
    CB_PROF_STATS,
    CB_PROF_SUBJECT,
    CB_PROF_SUBJECTS,
    UD_PROFILE_PERIOD,
)
from db.repositories import (
    PERIOD_ALL,
    PERIOD_MONTH,
    PERIOD_SEMESTER,
    PERIOD_WEEK,
    activate_subscription,
    get_activity_statistics,
    get_deadline_statistics,
    get_materials_statistics,
    get_period_window,
    get_profile_overview,
    get_statistics_overview,
    get_subscription_status,
    get_subject_detail_stats,
    get_subject_progress_stats,
)
from handlers.achievements import open_from_profile as open_achievements
from services.profile import (
    get_activity_stats_keyboard,
    get_activity_stats_text,
    get_deadlines_stats_keyboard,
    get_deadlines_stats_text,
    get_materials_stats_keyboard,
    get_materials_stats_text,
    get_period_picker_keyboard,
    get_period_picker_text,
    get_subscription_checkout_keyboard,
    get_profile_hub_keyboard,
    get_profile_hub_text,
    get_subscription_keyboard,
    get_subscription_manage_keyboard,
    get_subscription_manage_text,
    get_subscription_text,
    get_statistics_hub_keyboard,
    get_statistics_hub_text,
    get_subject_detail_keyboard,
    get_subject_detail_text,
    get_subjects_stats_keyboard,
    get_subjects_stats_text,
)

_HTML = ParseMode.HTML
_VALID_PERIODS = {PERIOD_WEEK, PERIOD_MONTH, PERIOD_SEMESTER, PERIOD_ALL}
_SUBSCRIPTION_PAYLOAD = "lovestudy:pro:monthly:v1"
_SUBSCRIPTION_PERIOD_SECONDS = 30 * 24 * 60 * 60
_SUBSCRIPTION_PERIOD_DAYS = 30
_SUBSCRIPTION_TITLE = "LoveStudy Pro"


async def _safe_edit(query, text: str, keyboard) -> None:
    try:
        await query.edit_message_text(text, reply_markup=keyboard, parse_mode=_HTML)
    except BadRequest:
        await query.message.reply_text(text, reply_markup=keyboard, parse_mode=_HTML)


def _get_period_key(context: ContextTypes.DEFAULT_TYPE) -> str:
    value = context.user_data.get(UD_PROFILE_PERIOD, PERIOD_WEEK)
    return value if value in _VALID_PERIODS else PERIOD_WEEK


def _set_period_key(context: ContextTypes.DEFAULT_TYPE, value: str) -> None:
    context.user_data[UD_PROFILE_PERIOD] = value if value in _VALID_PERIODS else PERIOD_WEEK


async def open_profile_hub(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    uid = update.effective_user.id
    async with context.bot_data["session_factory"]() as session:
        overview = await get_profile_overview(session, uid)

    if overview is None:
        await query.answer("Профиль пока недоступен", show_alert=True)
        return

    await _safe_edit(query, get_profile_hub_text(overview), get_profile_hub_keyboard())


async def open_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    uid = update.effective_user.id
    async with context.bot_data["session_factory"]() as session:
        status = await get_subscription_status(session, uid)

    price_stars = get_subscription_price_stars()
    await _safe_edit(query, get_subscription_text(status, price_stars), get_subscription_keyboard(status))


async def open_subscription_manage(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    uid = update.effective_user.id
    async with context.bot_data["session_factory"]() as session:
        status = await get_subscription_status(session, uid)

    await _safe_edit(query, get_subscription_manage_text(status), get_subscription_manage_keyboard())


async def start_subscription_checkout(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    price_stars = get_subscription_price_stars()
    invoice_url = await context.bot.create_invoice_link(
        title=_SUBSCRIPTION_TITLE,
        description=(
            "Безлимитная генерация тестов в LoveStudy. "
            "Подписка продлевается каждые 30 дней через Telegram Stars."
        ),
        payload=_SUBSCRIPTION_PAYLOAD,
        currency="XTR",
        prices=[LabeledPrice("LoveStudy Pro / 30 дней", price_stars)],
        provider_token="",
        subscription_period=_SUBSCRIPTION_PERIOD_SECONDS,
    )
    await _safe_edit(
        query,
        (
            "⭐ <b>Оформление LoveStudy Pro</b>\n\n"
            f"Стоимость: {price_stars} Stars в 30 дней.\n"
            "Нажми кнопку ниже: Telegram откроет безопасный checkout и оформит подписку."
        ),
        get_subscription_checkout_keyboard(invoice_url),
    )


async def on_pre_checkout_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.pre_checkout_query
    if query is None:
        return

    if query.invoice_payload != _SUBSCRIPTION_PAYLOAD:
        await query.answer(ok=False, error_message="Не удалось подтвердить оплату подписки.")
        return

    await query.answer(ok=True)


async def on_successful_payment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    payment = message.successful_payment if message else None
    if payment is None or payment.invoice_payload != _SUBSCRIPTION_PAYLOAD:
        return

    async with context.bot_data["session_factory"]() as session:
        status = await activate_subscription(
            session,
            update.effective_user.id,
            duration_days=_SUBSCRIPTION_PERIOD_DAYS,
            expires_at=payment.subscription_expiration_date,
            provider_charge_id=payment.provider_payment_charge_id,
            telegram_charge_id=payment.telegram_payment_charge_id,
        )

    price_stars = get_subscription_price_stars()
    await message.reply_text(
        get_subscription_text(status, price_stars),
        reply_markup=get_subscription_keyboard(status),
        parse_mode=_HTML,
    )


async def open_statistics_hub(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    await _render_statistics_hub(query, update.effective_user.id, context)


async def _render_statistics_hub(query, user_id: int, context: ContextTypes.DEFAULT_TYPE) -> None:
    period_key = _get_period_key(context)
    async with context.bot_data["session_factory"]() as session:
        overview = await get_statistics_overview(session, user_id, period_key)

    await _safe_edit(query, get_statistics_hub_text(overview), get_statistics_hub_keyboard())


async def open_period_picker(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    period = get_period_window(_get_period_key(context))
    await _safe_edit(
        query,
        get_period_picker_text(period.label),
        get_period_picker_keyboard(period.key),
    )


async def set_period(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    period_key = query.data[len(CB_PROF_PERIOD_SET):]
    _set_period_key(context, period_key)
    await _render_statistics_hub(query, update.effective_user.id, context)


async def open_subjects_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    uid = update.effective_user.id
    period = get_period_window(_get_period_key(context))
    async with context.bot_data["session_factory"]() as session:
        items = await get_subject_progress_stats(session, uid, period.key)

    await _safe_edit(
        query,
        get_subjects_stats_text(items, period.label),
        get_subjects_stats_keyboard(items),
    )


async def open_subject_detail(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    try:
        subject_id = int(query.data[len(CB_PROF_SUBJECT):])
    except ValueError:
        await query.answer("Не удалось открыть предмет", show_alert=True)
        return

    uid = update.effective_user.id
    period = get_period_window(_get_period_key(context))
    async with context.bot_data["session_factory"]() as session:
        item = await get_subject_detail_stats(session, uid, subject_id, period.key)

    if item is None:
        await query.answer("Предмет не найден", show_alert=True)
        return

    await _safe_edit(
        query,
        get_subject_detail_text(item, period.label),
        get_subject_detail_keyboard(),
    )


async def open_deadlines_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    uid = update.effective_user.id
    period = get_period_window(_get_period_key(context))
    async with context.bot_data["session_factory"]() as session:
        stats = await get_deadline_statistics(session, uid, period.key)

    await _safe_edit(
        query,
        get_deadlines_stats_text(stats, period.label),
        get_deadlines_stats_keyboard(),
    )


async def open_materials_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    uid = update.effective_user.id
    period = get_period_window(_get_period_key(context))
    async with context.bot_data["session_factory"]() as session:
        stats = await get_materials_statistics(session, uid, period.key)

    await _safe_edit(
        query,
        get_materials_stats_text(stats, period.label),
        get_materials_stats_keyboard(),
    )


async def open_activity_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    uid = update.effective_user.id
    period = get_period_window(_get_period_key(context))
    async with context.bot_data["session_factory"]() as session:
        stats = await get_activity_statistics(session, uid, period.key)

    await _safe_edit(
        query,
        get_activity_stats_text(stats, period.label),
        get_activity_stats_keyboard(),
    )


def register(app: Application) -> None:
    mapping = [
        (CB_MAIN_PROFILE, open_profile_hub),
        (CB_PROF_SUBSCRIPTION, open_subscription),
        (CB_PROF_SUB_BUY, start_subscription_checkout),
        (CB_PROF_SUB_MANAGE, open_subscription_manage),
        (CB_PROF_ACHIEV, open_achievements),
        (CB_PROF_STATS, open_statistics_hub),
        (CB_PROF_SUBJECTS, open_subjects_stats),
        (CB_PROF_DEADLINES, open_deadlines_stats),
        (CB_PROF_MATERIALS, open_materials_stats),
        (CB_PROF_ACTIVITY, open_activity_stats),
        (CB_PROF_PERIOD, open_period_picker),
    ]
    for cb, handler in mapping:
        app.add_handler(CallbackQueryHandler(handler, pattern=rf"^{re.escape(cb)}$"))

    app.add_handler(CallbackQueryHandler(set_period, pattern=rf"^{re.escape(CB_PROF_PERIOD_SET)}"))
    app.add_handler(CallbackQueryHandler(open_subject_detail, pattern=rf"^{re.escape(CB_PROF_SUBJECT)}"))
    app.add_handler(PreCheckoutQueryHandler(on_pre_checkout_query))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, on_successful_payment))
