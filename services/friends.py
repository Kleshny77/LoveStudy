# Тексты и клавиатуры для раздела «Друзья и рейтинг»

from html import escape

from telegram import CopyTextButton, InlineKeyboardMarkup

from db.repositories import get_learning_streak_days
from constants import (
    CB_FRI_INVITE, CB_FRI_LIST, CB_FRI_RATING,
    CB_FRIENDS, CB_NAV_MAIN,
)
from services.ui import BUTTON_PRIMARY, em, ib


# ──────────────────────────────────────────────
# Хаб «Друзья и рейтинг»
# ──────────────────────────────────────────────

def _streak_label(days: int) -> str:
    if days == 0:
        return "нет стрика"
    if days % 10 == 1 and days % 100 != 11:
        return f"{days} день"
    if days % 10 in (2, 3, 4) and days % 100 not in (12, 13, 14):
        return f"{days} дня"
    return f"{days} дней"


def _streak_motivation(days: int) -> str:
    if days == 0:
        return "Стрик начнет считаться после запуска раздела с тестами."
    if days < 3:
        return "Хорошее начало тестового стрика. Продолжай решать задания."
    if days < 7:
        return f"Ты держишь тестовый стрик уже {_streak_label(days)} подряд. Не останавливайся!"
    if days < 30:
        return f"Ты решаешь тесты уже {_streak_label(days)} подряд. Так держать!"
    return f"Легенда! {_streak_label(days)} тестового стрика — это серьёзно 🔥"


def get_hub_text(streak: int, friends_count: int, rank: int, total: int) -> str:
    return em(
        (
        f"🧠 <b>Твой стрик по тестам: {_streak_label(streak)}</b>\n\n"
        f"{_streak_motivation(streak)}\n\n"
        f"👥 Твоих друзей: {friends_count}\n"
        f"🏆 Твоё место в рейтинге: {rank} из {total}"
        )
    )


def get_hub_keyboard(has_friends: bool, invite_link: str = "") -> InlineKeyboardMarkup:
    if has_friends:
        return InlineKeyboardMarkup([
            [ib("🏆 Посмотреть рейтинг", callback_data=CB_FRI_RATING, style=BUTTON_PRIMARY)],
            [ib("👥 Мои друзья", callback_data=CB_FRI_LIST)],
            [ib("🔗 Пригласить друга", callback_data=CB_FRI_INVITE, style=BUTTON_PRIMARY)],
            [ib("🥇 Мои достижения", callback_data=CB_FRI_ACHIEV)],
            [ib("🔙 Назад", callback_data=CB_NAV_MAIN)],
        ])
    return InlineKeyboardMarkup([
        [ib("🔗 Пригласить друга — скопировать ссылку", copy_text=CopyTextButton(text=invite_link), style=BUTTON_PRIMARY)],
        [ib("🔙 Назад", callback_data=CB_NAV_MAIN)],
    ])


def get_hub_no_friends_text() -> str:
    return em(
        (
        "👥 <b>У тебя пока нет друзей</b>\n\n"
        "Пригласи одногруппников — и вы попадёте в общий рейтинг.\n\n"
        "Когда друг зарегистрируется:\n"
        "— вы появитесь в рейтинге друг у друга\n"
        "— будете видеть стрики\n"
        "— за каждого друга +1 защита стрика 🔥\n\n"
        "Нажми кнопку — ссылка сразу скопируется в буфер 👇"
        )
    )


# ──────────────────────────────────────────────
# Рейтинг
# ──────────────────────────────────────────────

def get_rating_text(ranking: list, my_id: int) -> str:
    lines = []
    my_rank = 1
    for user, rank in ranking:
        name = _friend_link_label(user)
        marker = " 👈 Ты" if user.telegram_id == my_id else ""
        if user.telegram_id == my_id:
            my_rank = rank
        streak = get_learning_streak_days(user)
        lines.append(f"{rank}. {name} — 🧠 {_streak_label(streak)}{marker}")

    body = "\n".join(lines) if lines else "Пока нет участников."
    return em(
        (
        f"🏆 <b>Рейтинг твоей группы</b>\n\n"
        f"Твоих друзей: {max(len(ranking) - 1, 0)}\n"
        f"Твоё место: {my_rank} из {len(ranking)}\n\n"
        f"{body}\n\n"
        "Чем длиннее тестовый стрик, тем выше ты в списке."
        )
    )


def get_rating_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [ib("🔗 Пригласить друга", callback_data=CB_FRI_INVITE, style=BUTTON_PRIMARY)],
        [
            ib("🔙 Назад", callback_data=CB_NAV_MAIN),
            ib("🏠 Главное меню", callback_data=CB_NAV_MAIN),
        ],
    ])


# ──────────────────────────────────────────────
# Мои друзья
# ──────────────────────────────────────────────

def _friend_link_label(user) -> str:
    name = escape(user.first_name or user.username or "Пользователь")
    if user.username:
        username = escape(user.username)
        return f'<a href="https://t.me/{username}">{name}</a>'
    return name


def get_friends_list_text(friends: list) -> str:
    if not friends:
        return em("👥 <b>Твои друзья (0)</b>\n\nПока никого нет.")
    lines = [f"{idx}. {_friend_link_label(friend)}" for idx, friend in enumerate(friends, start=1)]
    body = "\n".join(lines)
    note = "\n\nНажми на имя, чтобы открыть профиль в Telegram." if any(friend.username for friend in friends) else ""
    return em(f"👥 <b>Твои друзья ({len(friends)})</b>\n\n{body}{note}")


def get_friends_list_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [ib("🏆 Посмотреть рейтинг", callback_data=CB_FRI_RATING, style=BUTTON_PRIMARY)],
        [ib("🔗 Пригласить друга", callback_data=CB_FRI_INVITE, style=BUTTON_PRIMARY)],
        [
            ib("🔙 Назад", callback_data=CB_FRIENDS),
            ib("🏠 Главное меню", callback_data=CB_NAV_MAIN),
        ],
    ])


# ──────────────────────────────────────────────
# Профиль пользователя
# ──────────────────────────────────────────────

def get_profile_text(user, materials_count: int, friends_count: int) -> str:
    name = user.first_name or user.username or "Пользователь"
    streak = get_learning_streak_days(user)
    return em(
        (
        f"👤 <b>{name}</b>\n"
        f"🧠 Стрик по тестам: {_streak_label(streak)}\n"
        f"🥇 Достижения: 0\n"
        f"📚 Добавлено материалов: {materials_count}\n"
        f"👥 Друзей: {friends_count}"
        )
    )


def get_profile_keyboard(back_cb: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            ib("🔙 Назад", callback_data=back_cb),
            ib("🏠 Главное меню", callback_data=CB_NAV_MAIN),
        ],
    ])


# ──────────────────────────────────────────────
# Поиск друга по @username
# ──────────────────────────────────────────────

def get_search_friend_text() -> str:
    return "Пришли ник друга через @\n\n<i>Например: @mikel37</i>"


def get_search_friend_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            ib("🔙 Назад", callback_data=CB_FRI_LIST),
            ib("🏠 Главное меню", callback_data=CB_NAV_MAIN),
        ],
    ])


# ──────────────────────────────────────────────
# Приглашение друга
# ──────────────────────────────────────────────

def get_invite_text(bot_username: str, user_id: int) -> str:
    link = f"t.me/{bot_username}?start=invite_{user_id}"
    return em(
        (
        "🔗 <b>Пригласи друга и соревнуйтесь вместе</b>\n\n"
        "Когда друг зарегистрируется:\n"
        "— вы появитесь в рейтинге\n"
        "— сможете делиться карточками\n"
        "— будете видеть стрики друг друга\n\n"
        f"Твоя ссылка:\n<code>{link}</code>\n\n"
        "За каждого друга +1 защита стрика 🔥"
        )
    )


def get_invite_keyboard(link: str, back_cb: str = CB_FRIENDS) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [ib("📋 Скопировать ссылку", copy_text=CopyTextButton(text=link), style=BUTTON_PRIMARY)],
        [
            ib("🔙 Назад", callback_data=back_cb),
            ib("🏠 Главное меню", callback_data=CB_NAV_MAIN),
        ],
    ])


# ──────────────────────────────────────────────
# Системные уведомления о стрике
# ──────────────────────────────────────────────

def get_streak_continued_text(days: int) -> str:
    return em(
        (
        f"🔥 <b>Твой стрик продлён!</b>\n"
        f"Ты уже {_streak_label(days)} подряд учишься без пропусков.\n"
        "Так держать!"
        )
    )


def get_streak_reset_text(old_days: int) -> str:
    return em(
        (
        f"💔 <b>Твой стрик сгорел</b>\n"
        f"Было: {_streak_label(old_days)}\n\n"
        "Начинаем заново? Сегодня отличный день 🔥"
        )
    )


def get_streak_notification_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [ib("Посмотреть рейтинг 🏆", callback_data=CB_FRI_RATING, style=BUTTON_PRIMARY)],
    ])


# ──────────────────────────────────────────────
# Уведомление о новом друге (для инвайтера)
# ──────────────────────────────────────────────

def get_new_friend_text(new_user_name: str, new_username: str | None) -> str:
    uname = f"@{new_username}" if new_username else new_user_name
    return em(
        (
        f"👥 <b>{uname} присоединился по ссылке!</b>\n"
        f"У тебя новый друг — {new_user_name}\n\n"
        "Теперь вы соревнуетесь в рейтинге 🔥"
        )
    )


def get_new_friend_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [ib("👥 Мои друзья", callback_data=CB_FRI_LIST, style=BUTTON_PRIMARY)],
        [
            ib("🔙 Назад", callback_data=CB_FRIENDS),
            ib("🏠 Главное меню", callback_data=CB_NAV_MAIN),
        ],
    ])


# ──────────────────────────────────────────────
# Мои достижения (placeholder)
# ──────────────────────────────────────────────

def get_achievements_text() -> str:
    return em(
        (
        "🥇 <b>Мои достижения</b>\n\n"
        "Раздел в разработке.\n"
        "Здесь появятся твои награды за стрики, материалы и помодоро-сессии."
        )
    )


def get_achievements_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            ib("🔙 Назад", callback_data=CB_FRIENDS),
            ib("🏠 Главное меню", callback_data=CB_NAV_MAIN),
        ],
    ])
