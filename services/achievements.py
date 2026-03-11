from telegram import InlineKeyboardMarkup

from constants import (
    CB_ACH_BACK,
    CB_ACH_DEADLINES,
    CB_ACH_DISCIPLINE,
    CB_ACH_HUB,
    CB_ACH_MATERIALS,
    CB_ACH_SERIES,
    CB_NAV_MAIN,
)
from db.repositories import AchievementCategory, AchievementItem, AchievementsOverview
from services.ui import em, ib

_CATEGORY_META = {
    "discipline": ("Учебная дисциплина", "📚"),
    "deadlines": ("Дедлайны", "⏰"),
    "materials": ("Материалы", "📎"),
    "series": ("Серии", "🔥"),
}

_CATEGORY_CALLBACKS = {
    "discipline": CB_ACH_DISCIPLINE,
    "deadlines": CB_ACH_DEADLINES,
    "materials": CB_ACH_MATERIALS,
    "series": CB_ACH_SERIES,
}


def _progress_suffix(item: AchievementItem) -> str:
    if item.current is None or item.target is None:
        return ""
    return f" ({min(item.current, item.target)}/{item.target})"


def _item_line(item: AchievementItem) -> str:
    marker = "🟢" if item.done else "⚪"
    return f"{marker} <b>{item.title}</b> — {item.description}{_progress_suffix(item)}"


def get_achievements_hub_text(overview: AchievementsOverview) -> str:
    return em(
        "🏆 <b>Раздел твоих достижений</b>\n"
        "Здесь ты видишь свой прогресс в учёбе. Выполняй задания, соблюдай дедлайны и собирай достижения разных категорий!\n\n"
        f"Открыто: {overview.unlocked_count} из {overview.total_count}\n\n"
        "Выбери категорию достижений, которую хочешь посмотреть:"
    )


def get_achievements_hub_keyboard() -> InlineKeyboardMarkup:
    rows = []
    ordered_keys = ("discipline", "deadlines", "materials", "series")
    for idx in range(0, len(ordered_keys), 2):
        pair = ordered_keys[idx : idx + 2]
        rows.append([
            ib(f"{_CATEGORY_META[key][1]} {_CATEGORY_META[key][0]}", callback_data=_CATEGORY_CALLBACKS[key])
            for key in pair
        ])
    rows.append([
        ib("🔙 Назад", callback_data=CB_ACH_BACK),
        ib("🏠 Главное меню", callback_data=CB_NAV_MAIN),
    ])
    return InlineKeyboardMarkup(rows)


def get_achievement_category_text(category: AchievementCategory) -> str:
    title, emoji = _CATEGORY_META.get(category.key, (category.title, "🏆"))
    lines = [f"{emoji} <b>{title}</b>", category.intro, ""]
    lines.extend(_item_line(item) for item in category.items)
    return em("\n".join(lines))


def get_achievement_category_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            ib("🔙 Назад", callback_data=CB_ACH_HUB),
            ib("🏠 Главное меню", callback_data=CB_NAV_MAIN),
        ],
    ])
