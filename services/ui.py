from __future__ import annotations

from telegram import CopyTextButton, InlineKeyboardButton

BUTTON_PRIMARY = "primary"
BUTTON_SUCCESS = "success"
BUTTON_DANGER = "danger"

# `RestrictedEmoji`: https://t.me/addemoji/RestrictedEmoji
# Храним mapping по самому emoji-символу, чтобы переиспользовать его и в тексте, и в кнопках.
CUSTOM_EMOJI_IDS: dict[str, str] = {
    "⏰": "5413704112220949842",
    "✅": "5427009714745517609",
    "✏️": "5334673106202010226",
    "❌": "5465665476971471368",
    "➕": "5226945370684140473",
    "🎉": "5436040291507247633",
    "🎓": "5375163339154399459",
    "🏆": "5409008750893734809",
    "🏠": "5465226866321268133",
    "👇": "5470177992950946662",
    "👋": "5472055112702629499",
    "👤": "5373012449597335010",
    "👥": "5372926953978341366",
    "💔": "5471954395719539651",
    "💖": "5465540480538254161",
    "📂": "5431721976769027887",
    "📊": "5431577498364158238",
    "📎": "5377844313575150051",
    "📚": "5373098009640836781",
    "📝": "5334882760735598374",
    "📤": "5433614747381538714",
    "📥": "5433811242135331842",
    "🔄": "5264727218734524899",
    "🔔": "5242628160297641831",
    "🔗": "5375129357373165375",
    "🔥": "5420315771991497307",
    "🗂": "5431736674147114227",
    "😄": "5373330410321223066",
    "😉": "5373101475679443553",
    "🙂": "5371073319107827779",
    "🥇": "5280735858926822987",
    "🧠": "5237799019329105246",
}


def _sorted_emoji_keys() -> list[str]:
    return sorted(CUSTOM_EMOJI_IDS, key=len, reverse=True)


_PRIMARY_NAVIGATION_MARKERS = (
    "назад",
    "главное меню",
    "в главное меню",
)


def ce(key: str, fallback: str) -> str:
    emoji_id = CUSTOM_EMOJI_IDS.get(key)
    if not emoji_id:
        return fallback
    return f'<tg-emoji emoji-id="{emoji_id}">{fallback}</tg-emoji>'


def em(text: str) -> str:
    rendered = text
    for emoji in _sorted_emoji_keys():
        rendered = rendered.replace(emoji, ce(emoji, emoji))
    return rendered


def _extract_button_icon(text: str, icon_key: str | None) -> tuple[str, str | None]:
    if icon_key:
        emoji_id = CUSTOM_EMOJI_IDS.get(icon_key)
        return text, emoji_id

    for emoji in _sorted_emoji_keys():
        emoji_id = CUSTOM_EMOJI_IDS[emoji]
        prefix = f"{emoji} "
        suffix = f" {emoji}"
        if text.startswith(prefix):
            return text[len(prefix):], emoji_id
        if text.endswith(suffix):
            return text[: -len(suffix)], emoji_id
    return text, None


def _is_primary_navigation(text: str) -> bool:
    normalized = text.strip().lower()
    return any(marker in normalized for marker in _PRIMARY_NAVIGATION_MARKERS)


def ib(
    text: str,
    *,
    callback_data: str | None = None,
    url: str | None = None,
    copy_text: CopyTextButton | None = None,
    style: str | None = None,
    icon_key: str | None = None,
) -> InlineKeyboardButton:
    button_text, emoji_id = _extract_button_icon(text, icon_key)

    api_kwargs: dict[str, str] = {}
    if style == BUTTON_PRIMARY and not _is_primary_navigation(button_text):
        style = None
    elif style is None and _is_primary_navigation(button_text):
        style = BUTTON_PRIMARY
    if style:
        api_kwargs["style"] = style
    if emoji_id:
        api_kwargs["icon_custom_emoji_id"] = emoji_id

    kwargs = {
        "text": button_text,
        "callback_data": callback_data,
        "url": url,
        "copy_text": copy_text,
    }
    if api_kwargs:
        kwargs["api_kwargs"] = api_kwargs
    return InlineKeyboardButton(**kwargs)
