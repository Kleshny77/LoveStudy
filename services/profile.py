from db.repositories import (
    ActivityStats,
    DeadlineStats,
    MaterialsStats,
    ProfileOverview,
    StatisticsOverview,
    SubjectProgressItem,
    get_learning_streak_days,
)
from telegram import InlineKeyboardMarkup

from constants import (
    CB_NAV_MAIN,
    CB_MAIN_PROFILE,
    CB_PROF_ACHIEV,
    CB_PROF_ACTIVITY,
    CB_PROF_DEADLINES,
    CB_PROF_MATERIALS,
    CB_PROF_PERIOD,
    CB_PROF_PERIOD_SET,
    CB_PROF_STATS,
    CB_PROF_SUBJECT,
    CB_PROF_SUBJECTS,
)
from services.ui import BUTTON_PRIMARY, em, ib


def _format_minutes_as_hours(minutes: int | float) -> str:
    hours = round(float(minutes) / 60, 1)
    label = f"{hours:.1f}".replace(".", ",")
    return f"{label} ч"


def get_profile_hub_text(overview: ProfileOverview) -> str:
    name = overview.user.first_name or overview.user.username or "друг"
    streak = get_learning_streak_days(overview.user)
    return em(
        (
        f"👤 <b>Добро пожаловать в твой профиль, {name}!</b>\n\n"
        "Выбери категорию, которую хочешь посмотреть.\n\n"
        f"🧠 Стрик по тестам: {streak}\n"
        f"📚 Предметов: {overview.subjects_count}\n"
        f"📎 Материалов: {overview.materials_count}\n"
        f"🍅 Фокус-сессий помодоро: {overview.total_focus_sessions}"
        )
    )


def get_profile_hub_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [ib("🏆 Мои достижения", callback_data=CB_PROF_ACHIEV)],
        [ib("📊 Статистика", callback_data=CB_PROF_STATS, style=BUTTON_PRIMARY)],
        [ib("🔙 Назад", callback_data=CB_NAV_MAIN)],
    ])


def _achievement_rows(overview: ProfileOverview) -> list[tuple[bool, str]]:
    streak = get_learning_streak_days(overview.user)
    return [
        (overview.materials_count >= 1, "Первый материал: добавь 1+ материал"),
        (overview.materials_count >= 10, "Коллекционер: собери 10+ материалов"),
        (streak >= 3, "Тестовый ритм: удерживай стрик тестов 3+ дня"),
        (overview.total_focus_sessions >= 5, "Фокус-машина: заверши 5+ помодоро-сессий"),
        (overview.friends_count >= 1, "Командный игрок: добавь хотя бы одного друга"),
    ]


def get_achievements_text(overview: ProfileOverview) -> str:
    rows = _achievement_rows(overview)
    earned = sum(1 for done, _ in rows if done)
    lines = [f"{'✅' if done else '▫️'} {title}" for done, title in rows]
    return em(
        (
        f"🏆 <b>Мои достижения</b>\n\n"
        f"Открыто: {earned} из {len(rows)}\n\n"
        + "\n".join(lines)
        )
    )


def get_achievements_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            ib("🔙 Назад", callback_data=CB_MAIN_PROFILE),
            ib("🏠 Главное меню", callback_data=CB_NAV_MAIN),
        ],
    ])


def get_statistics_hub_text(overview: StatisticsOverview) -> str:
    return em(
        (
        "📊 <b>Твой учебный прогресс</b>\n"
        "Здесь собрана статистика по учёбе за выбранный период.\n\n"
        f"🗓 Период: {overview.period.label}\n\n"
        f"📚 Активных предметов: {overview.active_subjects}\n"
        f"📎 Материалов за период: {overview.materials_added}\n"
        f"🍅 Фокус-времени: {_format_minutes_as_hours(overview.focus_minutes)}\n"
        f"⏰ Дедлайнов в периоде: {overview.deadlines_total}"
        )
    )


def get_statistics_hub_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            ib("📚 Предметы", callback_data=CB_PROF_SUBJECTS),
            ib("⏰ Дедлайны", callback_data=CB_PROF_DEADLINES, style=BUTTON_PRIMARY),
        ],
        [
            ib("📎 Материалы", callback_data=CB_PROF_MATERIALS),
            ib("🔥 Активность", callback_data=CB_PROF_ACTIVITY),
        ],
        [ib("🗓 Выбрать период", callback_data=CB_PROF_PERIOD, style=BUTTON_PRIMARY)],
        [
            ib("🔙 Назад", callback_data=CB_MAIN_PROFILE),
            ib("🏠 Главное меню", callback_data=CB_NAV_MAIN),
        ],
    ])


def get_period_picker_text(period_label: str) -> str:
    return em(
        (
        "🗓 <b>Выбери период для анализа прогресса</b>\n\n"
        f"Сейчас выбран: {period_label}"
        )
    )


def get_period_picker_keyboard(selected_key: str) -> InlineKeyboardMarkup:
    def label(key: str, text: str) -> str:
        return f"{text} {'✅' if key == selected_key else ''}".rstrip()

    return InlineKeyboardMarkup([
        [ib(label("week", "📅 Текущая неделя"), callback_data=f"{CB_PROF_PERIOD_SET}week")],
        [ib(label("month", "🗓 Текущий месяц"), callback_data=f"{CB_PROF_PERIOD_SET}month")],
        [ib(label("semester", "🎓 Семестр"), callback_data=f"{CB_PROF_PERIOD_SET}semester")],
        [ib(label("all", "⚪ Всё время"), callback_data=f"{CB_PROF_PERIOD_SET}all")],
        [
            ib("🔙 Назад", callback_data=CB_PROF_STATS),
            ib("🏠 Главное меню", callback_data=CB_NAV_MAIN),
        ],
    ])


def get_subjects_stats_text(items: list[SubjectProgressItem], period_label: str) -> str:
    if not items:
        return em(
            (
            "📚 <b>Прогресс по предметам</b>\n\n"
            f"Период: {period_label}\n\n"
            "Пока нет предметов. Как только добавишь материалы, здесь появится статистика."
            )
        )

    lines = [
        f"{item.subject_name} — выучено {item.learned_materials}/{item.total_materials}, активность {item.active_days} дн."
        for item in items
    ]
    return em(
        (
        "📚 <b>Прогресс по предметам</b>\n\n"
        f"Период: {period_label}\n\n"
        + "\n".join(lines)
        )
    )


def get_subjects_stats_keyboard(items: list[SubjectProgressItem]) -> InlineKeyboardMarkup:
    rows = [
        [ib(item.subject_name, callback_data=f"{CB_PROF_SUBJECT}{item.subject_id}")]
        for item in items
    ]
    rows.append([
        ib("🔙 Назад", callback_data=CB_PROF_STATS),
        ib("🏠 Главное меню", callback_data=CB_NAV_MAIN),
    ])
    return InlineKeyboardMarkup(rows)


def get_subject_detail_text(item: SubjectProgressItem, period_label: str) -> str:
    if item.progress_percent >= 100 and item.total_materials > 0:
        note = "Предмет полностью закрыт: все материалы уже отмечены как выученные."
    elif item.progress_percent >= 50:
        note = "Хороший прогресс. Осталось добить оставшиеся материалы."
    else:
        note = "Начало положено. Продолжай проходить тесты по материалам, чтобы закрывать предмет."

    return em(
        (
        f"📘 <b>{item.subject_name}</b>\n\n"
        f"Период: {period_label}\n\n"
        f"🧠 Выучено материалов: {item.learned_materials}/{item.total_materials}\n"
        f"📈 Прогресс по предмету: {item.progress_percent}%\n"
        f"📎 Активностей по материалам за период: {item.period_materials}\n"
        f"🔥 Активных дней: {item.active_days}\n"
        f"🗂 Прогресс обновляется после прохождения тестов по материалам.\n\n"
        f"{note}"
        )
    )


def get_subject_detail_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            ib("🔙 Назад", callback_data=CB_PROF_SUBJECTS),
            ib("🏠 Главное меню", callback_data=CB_NAV_MAIN),
        ],
    ])


def get_materials_stats_text(stats: MaterialsStats, period_label: str) -> str:
    return em(
        (
        "📎 <b>Материалы</b>\n\n"
        f"Период: {period_label}\n\n"
        f"Всего материалов: {stats.total}\n"
        f"Конспекты и документы: {stats.docs_and_pdfs}\n"
        f"Ссылки: {stats.links}\n"
        f"Медиа: {stats.media}\n"
        f"Архивы: {stats.archives}\n"
        f"Другое: {stats.other}"
        )
    )


def get_materials_stats_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            ib("🔙 Назад", callback_data=CB_PROF_STATS),
            ib("🏠 Главное меню", callback_data=CB_NAV_MAIN),
        ],
    ])


def get_deadlines_stats_text(stats: DeadlineStats, period_label: str) -> str:
    body = (
        f"Всего дедлайнов: {stats.total}\n"
        f"Выполнено вовремя: {stats.completed_on_time}\n"
        f"Просрочено: {stats.overdue}\n"
        f"В работе: {stats.in_progress}"
    )
    if stats.total == 0:
        body += "\n\nКогда начнём заполнять раздел дедлайнов, здесь автоматически появится динамика."
    return em(
        (
        "⏰ <b>Дедлайны</b>\n\n"
        f"Период: {period_label}\n\n"
        f"{body}"
        )
    )


def get_deadlines_stats_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            ib("🔙 Назад", callback_data=CB_PROF_STATS),
            ib("🏠 Главное меню", callback_data=CB_NAV_MAIN),
        ],
    ])


def get_activity_stats_text(stats: ActivityStats, period_label: str) -> str:
    return em(
        (
        "🔥 <b>Учебная активность</b>\n\n"
        f"Период: {period_label}\n\n"
        f"Активных дней: {stats.active_days}\n"
        f"Фокус-времени: {_format_minutes_as_hours(stats.total_focus_minutes)}\n"
        f"Средний фокус за активный день: {_format_minutes_as_hours(stats.average_focus_minutes)}\n"
        f"Завершённых помодоро: {stats.pomodoro_sessions}\n"
        f"Добавлено материалов: {stats.materials_added}\n"
        f"Стрик по тестам: {stats.current_streak}\n\n"
        "Активность считается по материалам, помодоро и пройденным тестам."
        )
    )


def get_activity_stats_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            ib("🔙 Назад", callback_data=CB_PROF_STATS),
            ib("🏠 Главное меню", callback_data=CB_NAV_MAIN),
        ],
    ])
