# слой доступа к данным

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from db.connection import get_engine
from db.models import Deadline, DeadlineSettings, Friendship, Material, PomodoroSessionLog, PomodoroSettings, Subject, TelegramUXSettings, User

# ──────────────────────────────────────────────
# Вспомогательные константы типов материалов
# ──────────────────────────────────────────────

_ARCHIVE_EXTS = {".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz", ".tgz", ".tar.gz"}

MATERIAL_TYPE_LINK    = "Ссылка"
MATERIAL_TYPE_FILE    = "Файл"
MATERIAL_TYPE_ARCHIVE = "Архив"
MATERIAL_TYPE_IMAGE   = "Изображение"
MATERIAL_TYPE_VIDEO   = "Видео"
MATERIAL_TYPE_AUDIO   = "Аудио"
MATERIAL_TYPE_PDF     = "PDF"
MATERIAL_TYPE_DOC     = "Документ"

PERIOD_WEEK = "week"
PERIOD_MONTH = "month"
PERIOD_SEMESTER = "semester"
PERIOD_ALL = "all"
TEST_STREAK_ENABLED = True  # стрик считается по прохождению тестов
QUIZ_GENERATIONS_PER_DAY = 15


@dataclass(slots=True)
class PeriodWindow:
    key: str
    label: str
    start: datetime | None
    end: datetime | None


@dataclass(slots=True)
class ProfileOverview:
    user: User
    subjects_count: int
    materials_count: int
    friends_count: int
    total_focus_sessions: int
    total_focus_minutes: int


@dataclass(slots=True)
class StatisticsOverview:
    period: PeriodWindow
    active_subjects: int
    materials_added: int
    focus_minutes: int
    deadlines_total: int


@dataclass(slots=True)
class SubjectProgressItem:
    subject_id: int
    subject_name: str
    total_materials: int
    learned_materials: int
    period_materials: int
    active_days: int
    progress_percent: int


@dataclass(slots=True)
class MaterialsStats:
    total: int
    docs_and_pdfs: int
    links: int
    media: int
    archives: int
    other: int


@dataclass(slots=True)
class DeadlineStats:
    total: int
    completed_on_time: int
    overdue: int
    in_progress: int


@dataclass(slots=True)
class DeadlineSettingsData:
    reminders_enabled: bool
    daily_digest_enabled: bool
    daily_digest_time: str


@dataclass(slots=True)
class ActivityStats:
    active_days: int
    current_streak: int
    total_focus_minutes: int
    average_focus_minutes: float
    pomodoro_sessions: int
    materials_added: int


@dataclass(slots=True)
class QuizGenerationStatus:
    allowed: bool
    used_today: int
    remaining_today: int
    next_reset_at: datetime


@dataclass(slots=True)
class SubscriptionStatus:
    is_active: bool
    expires_at: datetime | None


@dataclass(slots=True)
class TelegramUXSettingsData:
    study_chat_id: int | None
    study_chat_title: str | None
    study_chat_username: str | None
    focus_buddy_id: int | None
    focus_buddy_name: str | None
    focus_buddy_username: str | None
    focus_buddy_enabled: bool


@dataclass(slots=True)
class AchievementItem:
    title: str
    description: str
    done: bool
    current: int | None = None
    target: int | None = None


@dataclass(slots=True)
class AchievementCategory:
    key: str
    title: str
    intro: str
    items: list[AchievementItem]


@dataclass(slots=True)
class AchievementsOverview:
    unlocked_count: int
    total_count: int
    categories: list[AchievementCategory]


def detect_material_type(filename: str | None, mime_type: str | None) -> str:
    """Определяет тип материала по имени файла и MIME-типу."""
    if filename:
        name = filename.lower()
        # проверяем двойные расширения (.tar.gz)
        for ext in _ARCHIVE_EXTS:
            if name.endswith(ext):
                return MATERIAL_TYPE_ARCHIVE

    if mime_type:
        m = mime_type.lower()
        if any(k in m for k in ("zip", "rar", "7z", "tar", "archive", "compressed")):
            return MATERIAL_TYPE_ARCHIVE
        if m == "application/pdf":
            return MATERIAL_TYPE_PDF
        if m.startswith("image/"):
            return MATERIAL_TYPE_IMAGE
        if m.startswith("video/"):
            return MATERIAL_TYPE_VIDEO
        if m.startswith("audio/"):
            return MATERIAL_TYPE_AUDIO
        if any(k in m for k in ("word", "document", "text/", "presentation", "powerpoint", "excel", "spreadsheet")):
            return MATERIAL_TYPE_DOC

    return MATERIAL_TYPE_FILE


def get_period_window(period_key: str, now: datetime | None = None) -> PeriodWindow:
    current = now or datetime.now(timezone.utc)
    current = current.astimezone(timezone.utc)

    if period_key == PERIOD_MONTH:
        start = current.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if start.month == 12:
            end = start.replace(year=start.year + 1, month=1)
        else:
            end = start.replace(month=start.month + 1)
        return PeriodWindow(PERIOD_MONTH, "текущий месяц", start, end)

    if period_key == PERIOD_SEMESTER:
        year = current.year
        month = current.month
        if month >= 9:
            start = datetime(year, 9, 1, tzinfo=timezone.utc)
        elif month == 1:
            start = datetime(year - 1, 9, 1, tzinfo=timezone.utc)
        else:
            start = datetime(year, 2, 1, tzinfo=timezone.utc)
        return PeriodWindow(PERIOD_SEMESTER, "семестр", start, current + timedelta(seconds=1))

    if period_key == PERIOD_ALL:
        return PeriodWindow(PERIOD_ALL, "всё время", None, None)

    start_of_day = datetime.combine(current.date(), time.min, tzinfo=timezone.utc)
    start = start_of_day - timedelta(days=current.weekday())
    end = start + timedelta(days=7)
    return PeriodWindow(PERIOD_WEEK, "текущая неделя", start, end)


def _in_period(column, window: PeriodWindow):
    if window.start is None or window.end is None:
        return None
    return and_(column >= window.start, column < window.end)


def _max_consecutive_days(days: set[date]) -> int:
    if not days:
        return 0
    ordered = sorted(days)
    best = current = 1
    for previous, current_day in zip(ordered, ordered[1:]):
        if (current_day - previous).days == 1:
            current += 1
            best = max(best, current)
        else:
            current = 1
    return best


def _on_time_deadline_streak(deadlines: list[Deadline]) -> int:
    completed = [d for d in deadlines if d.completed_at is not None]
    completed.sort(key=lambda item: item.completed_at or item.due_at)
    best = current = 0
    for deadline in completed:
        if deadline.completed_at is not None and deadline.completed_at <= deadline.due_at:
            current += 1
            best = max(best, current)
        else:
            current = 0
    return best


def get_learning_streak_days(user: User | None) -> int:
    """Пока стрик завязан на будущий раздел с тестами, в проде не показываем daily-visit логику."""
    if user is None or not TEST_STREAK_ENABLED:
        return 0
    return max(int(user.streak_days or 0), 0)


# ──────────────────────────────────────────────
# Session factory
# ──────────────────────────────────────────────

def get_session_factory() -> async_sessionmaker[AsyncSession] | None:
    engine = get_engine()
    if engine is None:
        return None
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


# ──────────────────────────────────────────────
# Users
# ──────────────────────────────────────────────

async def get_or_create_user(
    session: AsyncSession,
    telegram_id: int,
    username: str | None,
    first_name: str | None,
) -> User:
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()
    if user is not None:
        changed = False
        if user.username != username:
            user.username = username
            changed = True
        if user.first_name != first_name:
            user.first_name = first_name
            changed = True
        if changed:
            await session.commit()
        return user
    user = User(telegram_id=telegram_id, username=username, first_name=first_name)
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


def _quiz_reset_at(now: datetime | None = None) -> datetime:
    current = now.astimezone() if now is not None else datetime.now().astimezone()
    tomorrow = current.date() + timedelta(days=1)
    tz = current.tzinfo or timezone.utc
    return datetime.combine(tomorrow, time.min, tzinfo=tz)


def has_active_subscription(user: User | None, now: datetime | None = None) -> bool:
    if user is None or user.subscription_expires_at is None:
        return False
    current = now or datetime.now(timezone.utc)
    expires_at = user.subscription_expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    return expires_at > current


async def _get_or_create_quiz_user(session: AsyncSession, user_telegram_id: int) -> User:
    result = await session.execute(select(User).where(User.telegram_id == user_telegram_id))
    user = result.scalar_one_or_none()
    if user is not None:
        return user
    user = User(telegram_id=user_telegram_id)
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def get_quiz_generation_status(
    session: AsyncSession,
    user_telegram_id: int,
    daily_limit: int = QUIZ_GENERATIONS_PER_DAY,
) -> QuizGenerationStatus:
    user = await _get_or_create_quiz_user(session, user_telegram_id)
    if has_active_subscription(user):
        return QuizGenerationStatus(
            allowed=True,
            used_today=int(user.quiz_generations_today or 0),
            remaining_today=daily_limit,
            next_reset_at=_quiz_reset_at(),
        )
    today = date.today()
    used_today = int(user.quiz_generations_today or 0)
    if user.quiz_generations_date != today:
        used_today = 0

    remaining_today = max(0, daily_limit - used_today)
    return QuizGenerationStatus(
        allowed=used_today < daily_limit,
        used_today=used_today,
        remaining_today=remaining_today,
        next_reset_at=_quiz_reset_at(),
    )


async def record_quiz_generation(
    session: AsyncSession,
    user_telegram_id: int,
    daily_limit: int = QUIZ_GENERATIONS_PER_DAY,
) -> QuizGenerationStatus:
    user = await _get_or_create_quiz_user(session, user_telegram_id)
    if has_active_subscription(user):
        return QuizGenerationStatus(
            allowed=True,
            used_today=int(user.quiz_generations_today or 0),
            remaining_today=daily_limit,
            next_reset_at=_quiz_reset_at(),
        )
    today = date.today()
    used_today = int(user.quiz_generations_today or 0)
    if user.quiz_generations_date != today:
        used_today = 0

    if used_today < daily_limit:
        used_today += 1
        user.quiz_generations_today = used_today
        user.quiz_generations_date = today
        await session.commit()

    remaining_today = max(0, daily_limit - used_today)
    return QuizGenerationStatus(
        allowed=used_today <= daily_limit,
        used_today=used_today,
        remaining_today=remaining_today,
        next_reset_at=_quiz_reset_at(),
    )


async def get_subscription_status(session: AsyncSession, user_telegram_id: int) -> SubscriptionStatus:
    user = await _get_or_create_quiz_user(session, user_telegram_id)
    expires_at = user.subscription_expires_at
    return SubscriptionStatus(
        is_active=has_active_subscription(user),
        expires_at=expires_at,
    )


async def activate_subscription(
    session: AsyncSession,
    user_telegram_id: int,
    *,
    duration_days: int = 30,
    expires_at: datetime | None = None,
    provider_charge_id: str | None = None,
    telegram_charge_id: str | None = None,
) -> SubscriptionStatus:
    user = await _get_or_create_quiz_user(session, user_telegram_id)
    now = datetime.now(timezone.utc)
    normalized_expires_at = expires_at
    if normalized_expires_at is not None and normalized_expires_at.tzinfo is None:
        normalized_expires_at = normalized_expires_at.replace(tzinfo=timezone.utc)

    if normalized_expires_at is not None:
        user.subscription_expires_at = normalized_expires_at
    else:
        current_expires_at = user.subscription_expires_at
        if current_expires_at is not None and current_expires_at.tzinfo is None:
            current_expires_at = current_expires_at.replace(tzinfo=timezone.utc)
        base_time = current_expires_at if current_expires_at and current_expires_at > now else now
        user.subscription_expires_at = base_time + timedelta(days=duration_days)
    if provider_charge_id:
        user.subscription_provider_charge_id = provider_charge_id
    if telegram_charge_id:
        user.subscription_telegram_charge_id = telegram_charge_id

    await session.commit()
    return SubscriptionStatus(
        is_active=True,
        expires_at=user.subscription_expires_at,
    )


async def get_telegram_ux_settings(
    session: AsyncSession,
    user_telegram_id: int,
) -> TelegramUXSettings:
    result = await session.execute(
        select(TelegramUXSettings).where(TelegramUXSettings.user_telegram_id == user_telegram_id)
    )
    settings = result.scalar_one_or_none()
    if settings is None:
        settings = TelegramUXSettings(user_telegram_id=user_telegram_id)
        session.add(settings)
        await session.commit()
        await session.refresh(settings)
    return settings


async def get_telegram_ux_settings_data(
    session: AsyncSession,
    user_telegram_id: int,
) -> TelegramUXSettingsData:
    settings = await get_telegram_ux_settings(session, user_telegram_id)
    return TelegramUXSettingsData(
        study_chat_id=settings.study_chat_id,
        study_chat_title=settings.study_chat_title,
        study_chat_username=settings.study_chat_username,
        focus_buddy_id=settings.focus_buddy_id,
        focus_buddy_name=settings.focus_buddy_name,
        focus_buddy_username=settings.focus_buddy_username,
        focus_buddy_enabled=bool(settings.focus_buddy_enabled and settings.focus_buddy_id),
    )


async def save_telegram_ux_settings(
    session: AsyncSession,
    user_telegram_id: int,
    *,
    study_chat_id: int | None = None,
    study_chat_title: str | None = None,
    study_chat_username: str | None = None,
    focus_buddy_id: int | None = None,
    focus_buddy_name: str | None = None,
    focus_buddy_username: str | None = None,
    focus_buddy_enabled: bool | None = None,
) -> TelegramUXSettingsData:
    settings = await get_telegram_ux_settings(session, user_telegram_id)

    if study_chat_id is not None or study_chat_title is not None or study_chat_username is not None:
        settings.study_chat_id = study_chat_id
        settings.study_chat_title = study_chat_title
        settings.study_chat_username = study_chat_username

    if focus_buddy_id is not None or focus_buddy_name is not None or focus_buddy_username is not None:
        settings.focus_buddy_id = focus_buddy_id
        settings.focus_buddy_name = focus_buddy_name
        settings.focus_buddy_username = focus_buddy_username
        settings.focus_buddy_enabled = focus_buddy_id is not None

    if focus_buddy_enabled is not None:
        settings.focus_buddy_enabled = focus_buddy_enabled and settings.focus_buddy_id is not None

    await session.commit()
    await session.refresh(settings)
    return TelegramUXSettingsData(
        study_chat_id=settings.study_chat_id,
        study_chat_title=settings.study_chat_title,
        study_chat_username=settings.study_chat_username,
        focus_buddy_id=settings.focus_buddy_id,
        focus_buddy_name=settings.focus_buddy_name,
        focus_buddy_username=settings.focus_buddy_username,
        focus_buddy_enabled=bool(settings.focus_buddy_enabled and settings.focus_buddy_id),
    )


# ──────────────────────────────────────────────
# Subjects
# ──────────────────────────────────────────────

async def get_user_subjects(
    session: AsyncSession,
    user_telegram_id: int,
) -> list[tuple[int, str]]:
    result = await session.execute(
        select(Subject.id, Subject.name)
        .where(Subject.user_telegram_id == user_telegram_id)
        .order_by(Subject.name)
    )
    return [(row[0], row[1]) for row in result.all()]


async def get_subject_by_id(
    session: AsyncSession,
    subject_id: int,
    user_telegram_id: int,
) -> Subject | None:
    result = await session.execute(
        select(Subject).where(
            Subject.id == subject_id,
            Subject.user_telegram_id == user_telegram_id,
        )
    )
    return result.scalar_one_or_none()


async def get_or_create_subject(
    session: AsyncSession,
    user_telegram_id: int,
    name: str,
) -> Subject:
    result = await session.execute(
        select(Subject).where(
            Subject.user_telegram_id == user_telegram_id,
            Subject.name == name,
        )
    )
    subject = result.scalar_one_or_none()
    if subject is not None:
        return subject
    subject = Subject(user_telegram_id=user_telegram_id, name=name.strip())
    session.add(subject)
    await session.flush()
    return subject


async def delete_subject(
    session: AsyncSession,
    subject_id: int,
    user_telegram_id: int,
) -> bool:
    """Удаляет предмет и все материалы внутри него."""
    subject = await get_subject_by_id(session, subject_id, user_telegram_id)
    if subject is None:
        return False

    materials = await get_materials_by_subject(session, subject_id, user_telegram_id)
    for material in materials:
        await session.delete(material)
    await session.delete(subject)
    await session.commit()
    return True


# ──────────────────────────────────────────────
# Deadlines
# ──────────────────────────────────────────────

async def get_deadline_settings(
    session: AsyncSession,
    user_telegram_id: int,
) -> DeadlineSettings:
    result = await session.execute(
        select(DeadlineSettings).where(DeadlineSettings.user_telegram_id == user_telegram_id)
    )
    settings = result.scalar_one_or_none()
    if settings is None:
        settings = DeadlineSettings(user_telegram_id=user_telegram_id)
        session.add(settings)
        await session.commit()
        await session.refresh(settings)
    return settings


async def save_deadline_settings(
    session: AsyncSession,
    user_telegram_id: int,
    **kwargs,
) -> DeadlineSettings:
    settings = await get_deadline_settings(session, user_telegram_id)
    for key, value in kwargs.items():
        setattr(settings, key, value)
    await session.commit()
    await session.refresh(settings)
    return settings


async def create_deadline(
    session: AsyncSession,
    user_telegram_id: int,
    subject_name: str,
    title: str,
    due_at: datetime,
    subject_id: int | None = None,
) -> Deadline:
    subject = None
    if subject_id is not None:
        subject = await get_subject_by_id(session, subject_id, user_telegram_id)
    if subject is None:
        subject = await get_or_create_subject(session, user_telegram_id, subject_name)

    deadline = Deadline(
        user_telegram_id=user_telegram_id,
        subject_id=subject.id,
        title=title.strip(),
        due_at=due_at,
    )
    session.add(deadline)
    await session.commit()
    await session.refresh(deadline)
    return deadline


async def list_active_deadlines(
    session: AsyncSession,
    user_telegram_id: int,
    limit: int | None = None,
) -> list[tuple[Deadline, str]]:
    stmt = (
        select(Deadline, Subject.name)
        .select_from(Deadline)
        .outerjoin(Subject, Subject.id == Deadline.subject_id)
        .where(
            Deadline.user_telegram_id == user_telegram_id,
            Deadline.completed_at.is_(None),
            Deadline.status != "deleted",
        )
        .order_by(Deadline.due_at)
    )
    if limit is not None:
        stmt = stmt.limit(limit)
    result = await session.execute(stmt)
    return [(deadline, subject_name or "Без предмета") for deadline, subject_name in result.all()]


async def list_deadline_subjects(
    session: AsyncSession,
    user_telegram_id: int,
) -> list[tuple[int, str]]:
    return await get_user_subjects(session, user_telegram_id)


async def list_subject_deadlines(
    session: AsyncSession,
    user_telegram_id: int,
    subject_id: int,
) -> list[Deadline]:
    result = await session.execute(
        select(Deadline)
        .where(
            Deadline.user_telegram_id == user_telegram_id,
            Deadline.subject_id == subject_id,
            Deadline.completed_at.is_(None),
            Deadline.status != "deleted",
        )
        .order_by(Deadline.due_at)
    )
    return list(result.scalars().all())


async def get_deadline_by_subject_index(
    session: AsyncSession,
    user_telegram_id: int,
    subject_id: int,
    index_1_based: int,
) -> Deadline | None:
    deadlines = await list_subject_deadlines(session, user_telegram_id, subject_id)
    if index_1_based < 1 or index_1_based > len(deadlines):
        return None
    return deadlines[index_1_based - 1]


async def complete_deadline(
    session: AsyncSession,
    user_telegram_id: int,
    deadline_id: int,
) -> Deadline | None:
    result = await session.execute(
        select(Deadline).where(
            Deadline.id == deadline_id,
            Deadline.user_telegram_id == user_telegram_id,
        )
    )
    deadline = result.scalar_one_or_none()
    if deadline is None:
        return None
    deadline.status = "completed"
    deadline.completed_at = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(deadline)
    return deadline


async def remove_deadline(
    session: AsyncSession,
    user_telegram_id: int,
    deadline_id: int,
) -> Deadline | None:
    result = await session.execute(
        select(Deadline).where(
            Deadline.id == deadline_id,
            Deadline.user_telegram_id == user_telegram_id,
        )
    )
    deadline = result.scalar_one_or_none()
    if deadline is None:
        return None
    deadline.status = "deleted"
    await session.commit()
    await session.refresh(deadline)
    return deadline


async def reschedule_deadline(
    session: AsyncSession,
    user_telegram_id: int,
    deadline_id: int,
    due_at: datetime,
) -> Deadline | None:
    result = await session.execute(
        select(Deadline).where(
            Deadline.id == deadline_id,
            Deadline.user_telegram_id == user_telegram_id,
        )
    )
    deadline = result.scalar_one_or_none()
    if deadline is None:
        return None
    deadline.due_at = due_at
    deadline.status = "open"
    deadline.reminder_sent_at = None
    await session.commit()
    await session.refresh(deadline)
    return deadline


async def set_deadline_reminder(
    session: AsyncSession,
    user_telegram_id: int,
    deadline_id: int,
    reminder_offset_minutes: int | None,
) -> Deadline | None:
    result = await session.execute(
        select(Deadline).where(
            Deadline.id == deadline_id,
            Deadline.user_telegram_id == user_telegram_id,
        )
    )
    deadline = result.scalar_one_or_none()
    if deadline is None:
        return None
    deadline.reminder_offset_minutes = reminder_offset_minutes
    deadline.reminder_sent_at = None
    await session.commit()
    await session.refresh(deadline)
    return deadline


async def get_due_deadline_reminders(
    session: AsyncSession,
    now: datetime,
) -> list[tuple[Deadline, DeadlineSettings, str]]:
    result = await session.execute(
        select(Deadline, DeadlineSettings, Subject.name)
        .select_from(Deadline)
        .join(DeadlineSettings, DeadlineSettings.user_telegram_id == Deadline.user_telegram_id)
        .outerjoin(Subject, Subject.id == Deadline.subject_id)
        .where(
            Deadline.completed_at.is_(None),
            Deadline.status == "open",
            Deadline.reminder_offset_minutes.is_not(None),
            Deadline.reminder_sent_at.is_(None),
            DeadlineSettings.reminders_enabled.is_(True),
            Deadline.due_at >= now - timedelta(minutes=1),
            Deadline.due_at <= now + timedelta(days=3),
        )
    )
    due_items: list[tuple[Deadline, DeadlineSettings, str]] = []
    for deadline, settings, subject_name in result.all():
        offset = deadline.reminder_offset_minutes or 0
        reminder_at = deadline.due_at - timedelta(minutes=offset)
        if reminder_at <= now <= deadline.due_at:
            due_items.append((deadline, settings, subject_name or "Без предмета"))
    return due_items


async def mark_deadline_reminder_sent(session: AsyncSession, deadline_id: int) -> None:
    result = await session.execute(select(Deadline).where(Deadline.id == deadline_id))
    deadline = result.scalar_one_or_none()
    if deadline is None:
        return
    deadline.reminder_sent_at = datetime.now(timezone.utc)
    await session.commit()


async def get_due_daily_digests(
    session: AsyncSession,
    current_time_hhmm: str,
    today: date,
) -> list[DeadlineSettings]:
    result = await session.execute(
        select(DeadlineSettings).where(
            DeadlineSettings.daily_digest_enabled.is_(True),
            DeadlineSettings.daily_digest_time == current_time_hhmm,
        )
    )
    settings = list(result.scalars().all())
    return [item for item in settings if item.last_daily_digest_date != today]


async def mark_daily_digest_sent(
    session: AsyncSession,
    user_telegram_id: int,
    today: date,
) -> None:
    settings = await get_deadline_settings(session, user_telegram_id)
    settings.last_daily_digest_date = today
    await session.commit()


async def get_upcoming_deadlines(
    session: AsyncSession,
    user_telegram_id: int,
    days_ahead: int = 7,
) -> list[tuple[Deadline, str]]:
    now = datetime.now(timezone.utc)
    until = now + timedelta(days=days_ahead)
    result = await session.execute(
        select(Deadline, Subject.name)
        .select_from(Deadline)
        .outerjoin(Subject, Subject.id == Deadline.subject_id)
        .where(
            Deadline.user_telegram_id == user_telegram_id,
            Deadline.completed_at.is_(None),
            Deadline.status == "open",
            Deadline.due_at >= now,
            Deadline.due_at <= until,
        )
        .order_by(Deadline.due_at)
    )
    return [(deadline, subject_name or "Без предмета") for deadline, subject_name in result.all()]


# ──────────────────────────────────────────────
# Materials
# ──────────────────────────────────────────────

async def save_file_to_subject(
    session: AsyncSession,
    user_telegram_id: int,
    subject_id: int,
    subject_name: str,
    telegram_file_id: str,
    file_unique_id: str,
    original_filename: str | None,
    file_size: int | None,
    mime_type: str | None,
) -> Material:
    """Сохраняет файл в уже существующую папку."""
    material_type = detect_material_type(original_filename, mime_type)
    material = Material(
        user_telegram_id=user_telegram_id,
        subject_id=subject_id,
        subject_name=subject_name,
        material_type=material_type,
        telegram_file_id=telegram_file_id,
        file_unique_id=file_unique_id,
        original_filename=original_filename,
        file_size=file_size,
        mime_type=mime_type,
    )
    session.add(material)
    await session.commit()
    await session.refresh(material)
    return material


async def save_file_to_new_subject(
    session: AsyncSession,
    user_telegram_id: int,
    subject_name: str,
    telegram_file_id: str,
    file_unique_id: str,
    original_filename: str | None,
    file_size: int | None,
    mime_type: str | None,
) -> Material:
    """Создаёт новую папку и сохраняет файл в неё."""
    subject = await get_or_create_subject(session, user_telegram_id, subject_name)
    material_type = detect_material_type(original_filename, mime_type)
    material = Material(
        user_telegram_id=user_telegram_id,
        subject_id=subject.id,
        subject_name=subject_name,
        material_type=material_type,
        telegram_file_id=telegram_file_id,
        file_unique_id=file_unique_id,
        original_filename=original_filename,
        file_size=file_size,
        mime_type=mime_type,
    )
    session.add(material)
    await session.commit()
    await session.refresh(material)
    return material


async def save_link_to_subject(
    session: AsyncSession,
    user_telegram_id: int,
    subject_id: int,
    subject_name: str,
    url: str,
    description: str | None = None,
) -> Material:
    """Сохраняет ссылку в уже существующую папку."""
    material = Material(
        user_telegram_id=user_telegram_id,
        subject_id=subject_id,
        subject_name=subject_name,
        material_type=MATERIAL_TYPE_LINK,
        url=url,
        original_filename=description,
    )
    session.add(material)
    await session.commit()
    await session.refresh(material)
    return material


async def save_link_to_new_subject(
    session: AsyncSession,
    user_telegram_id: int,
    subject_name: str,
    url: str,
    description: str | None = None,
) -> Material:
    """Создаёт новую папку и сохраняет ссылку в неё."""
    subject = await get_or_create_subject(session, user_telegram_id, subject_name)
    material = Material(
        user_telegram_id=user_telegram_id,
        subject_id=subject.id,
        subject_name=subject_name,
        material_type=MATERIAL_TYPE_LINK,
        url=url,
        original_filename=description,
    )
    session.add(material)
    await session.commit()
    await session.refresh(material)
    return material


# ──────────────────────────────────────────────
# Запросы для просмотра материалов
# ──────────────────────────────────────────────

async def get_materials_by_subject(
    session: AsyncSession,
    subject_id: int,
    user_telegram_id: int,
) -> list[Material]:
    """Все материалы предмета, отсортированные по дате добавления."""
    result = await session.execute(
        select(Material)
        .where(
            Material.subject_id == subject_id,
            Material.user_telegram_id == user_telegram_id,
        )
        .order_by(Material.created_at)
    )
    return list(result.scalars().all())


async def get_material_by_id(
    session: AsyncSession,
    material_id: int,
    user_telegram_id: int,
) -> Material | None:
    result = await session.execute(
        select(Material).where(
            Material.id == material_id,
            Material.user_telegram_id == user_telegram_id,
        )
    )
    return result.scalar_one_or_none()


async def delete_material(
    session: AsyncSession,
    material_id: int,
    user_telegram_id: int,
) -> bool:
    """Удаляет материал. Возвращает True если удалён, False если не найден."""
    material = await get_material_by_id(session, material_id, user_telegram_id)
    if not material:
        return False
    await session.delete(material)
    await session.commit()
    return True


# ──────────────────────────────────────────────
# Pomodoro settings
# ──────────────────────────────────────────────

async def get_pomo_settings(
    session: AsyncSession,
    user_telegram_id: int,
) -> PomodoroSettings:
    """Возвращает настройки помодоро, создавая дефолтные если их нет."""
    result = await session.execute(
        select(PomodoroSettings).where(PomodoroSettings.user_telegram_id == user_telegram_id)
    )
    settings = result.scalar_one_or_none()
    if settings is None:
        settings = PomodoroSettings(user_telegram_id=user_telegram_id)
        session.add(settings)
        await session.commit()
        await session.refresh(settings)
    return settings


async def save_pomo_settings(
    session: AsyncSession,
    user_telegram_id: int,
    **kwargs,
) -> PomodoroSettings:
    """Обновляет произвольные поля настроек помодоро."""
    settings = await get_pomo_settings(session, user_telegram_id)
    for key, value in kwargs.items():
        setattr(settings, key, value)
    await session.commit()
    await session.refresh(settings)
    return settings


async def increment_pomo_sessions(
    session: AsyncSession,
    user_telegram_id: int,
    work_minutes: int | None = None,
) -> int:
    """Увеличивает счётчик сессий сегодня. Сбрасывает если новый день."""
    settings = await get_pomo_settings(session, user_telegram_id)
    today = date.today()
    if settings.last_session_date != today:
        settings.sessions_today = 0
        settings.last_session_date = today
    settings.sessions_today += 1
    session.add(
        PomodoroSessionLog(
            user_telegram_id=user_telegram_id,
            work_minutes=work_minutes or settings.work_minutes,
        )
    )
    await session.commit()
    return settings.sessions_today


# Оставляем старые имена как алиасы — на случай если где-то ещё используются
async def create_material(
    session: AsyncSession,
    user_telegram_id: int,
    subject_name: str,
    material_type: str,
    telegram_file_id: str,
    original_filename: str,
    year: str | None,
    description: str | None,
) -> Material:
    subject = await get_or_create_subject(session, user_telegram_id, subject_name)
    material = Material(
        user_telegram_id=user_telegram_id,
        subject_id=subject.id,
        subject_name=subject_name,
        material_type=material_type,
        telegram_file_id=telegram_file_id,
        original_filename=original_filename,
        year=year,
        description=description,
    )
    session.add(material)
    await session.commit()
    await session.refresh(material)
    return material


async def create_material_to_subject(
    session: AsyncSession,
    user_telegram_id: int,
    subject_id: int,
    subject_name: str,
    telegram_file_id: str,
    original_filename: str,
) -> Material:
    return await save_file_to_subject(
        session,
        user_telegram_id=user_telegram_id,
        subject_id=subject_id,
        subject_name=subject_name,
        telegram_file_id=telegram_file_id,
        file_unique_id="",
        original_filename=original_filename,
        file_size=None,
        mime_type=None,
    )


# ──────────────────────────────────────────────
# Стрик пользователя
# ──────────────────────────────────────────────

async def update_streak(session: AsyncSession, user_telegram_id: int) -> tuple[int, str]:
    """Обновляет стрик при активности пользователя.
    Возвращает (новый_стрик, событие): 'continued' | 'started' | 'reset' | 'same'.
    """
    result = await session.execute(
        select(User).where(User.telegram_id == user_telegram_id)
    )
    user = result.scalar_one_or_none()
    if user is None:
        return 0, "same"

    today = date.today()
    event = "same"

    if user.last_activity_date is None:
        user.streak_days = 1
        user.last_activity_date = today
        event = "started"
    elif user.last_activity_date == today:
        event = "same"  # уже сегодня
    else:
        delta = (today - user.last_activity_date).days
        if delta == 1:
            user.streak_days += 1
            user.last_activity_date = today
            event = "continued"
        else:
            # пропустил день(и) — стрик сгорает
            old_streak = user.streak_days
            user.streak_days = 1
            user.last_activity_date = today
            event = "reset" if old_streak > 0 else "started"

    await session.commit()
    return user.streak_days, event


async def record_quiz_completion(
    session: AsyncSession,
    user_telegram_id: int,
    *,
    subject_id: int | None = None,
    material_id: int | None = None,
    correct_answers: int = 0,
    wrong_answers: int = 0,
    passed: bool = False,
) -> tuple[int, int]:
    """Сохраняет агрегированные результаты викторины и возвращает прогресс предмета."""
    user_result = await session.execute(
        select(User).where(User.telegram_id == user_telegram_id)
    )
    user = user_result.scalar_one_or_none()
    if user is not None:
        user.quiz_correct_answers = int(user.quiz_correct_answers or 0) + max(0, correct_answers)
        user.quiz_wrong_answers = int(user.quiz_wrong_answers or 0) + max(0, wrong_answers)

    now = datetime.now(timezone.utc)
    effective_subject_id = subject_id

    if material_id is not None:
        material = await get_material_by_id(session, material_id, user_telegram_id)
        if material is not None:
            material.quiz_correct_answers = int(material.quiz_correct_answers or 0) + max(0, correct_answers)
            material.quiz_wrong_answers = int(material.quiz_wrong_answers or 0) + max(0, wrong_answers)
            effective_subject_id = material.subject_id if material.subject_id is not None else effective_subject_id
            if passed and material.learned_at is None:
                material.learned_at = now
    elif effective_subject_id is not None and passed:
        materials = await get_materials_by_subject(session, effective_subject_id, user_telegram_id)
        for material in materials:
            if material.learned_at is None:
                material.learned_at = now

    await session.commit()

    if effective_subject_id is None:
        return 0, 0

    materials = await get_materials_by_subject(session, effective_subject_id, user_telegram_id)
    learned_count = sum(1 for material in materials if material.learned_at is not None)
    return learned_count, len(materials)


async def reset_user_streak(session: AsyncSession, user_telegram_id: int) -> None:
    result = await session.execute(
        select(User).where(User.telegram_id == user_telegram_id)
    )
    user = result.scalar_one_or_none()
    if user is None:
        return
    if user.streak_days == 0 and user.last_activity_date is None:
        return
    user.streak_days = 0
    user.last_activity_date = None
    await session.commit()


# ──────────────────────────────────────────────
# Друзья
# ──────────────────────────────────────────────

def _pair(a: int, b: int) -> tuple[int, int]:
    return (min(a, b), max(a, b))


async def get_friends(session: AsyncSession, user_telegram_id: int) -> list[User]:
    """Возвращает список пользователей-друзей."""
    uid = user_telegram_id
    result = await session.execute(
        select(Friendship).where(
            or_(Friendship.user1_id == uid, Friendship.user2_id == uid)
        )
    )
    friendships = result.scalars().all()
    friend_ids = [
        f.user2_id if f.user1_id == uid else f.user1_id
        for f in friendships
    ]
    if not friend_ids:
        return []
    users_result = await session.execute(
        select(User).where(User.telegram_id.in_(friend_ids))
    )
    return list(users_result.scalars().all())


async def are_friends(session: AsyncSession, user1: int, user2: int) -> bool:
    u1, u2 = _pair(user1, user2)
    result = await session.execute(
        select(Friendship).where(
            Friendship.user1_id == u1, Friendship.user2_id == u2
        )
    )
    return result.scalar_one_or_none() is not None


async def add_friend(session: AsyncSession, user1: int, user2: int) -> bool:
    """Создаёт дружбу. Возвращает True если добавлено, False если уже были друзья."""
    if user1 == user2:
        return False
    if await are_friends(session, user1, user2):
        return False
    u1, u2 = _pair(user1, user2)
    session.add(Friendship(user1_id=u1, user2_id=u2))
    await session.commit()
    return True


async def get_friends_rating(
    session: AsyncSession, user_telegram_id: int
) -> list[tuple[User, int]]:
    """Рейтинг: текущий пользователь + его друзья, отсортированные по стрику.
    Возвращает список (User, rank)."""
    friends = await get_friends(session, user_telegram_id)
    result = await session.execute(
        select(User).where(User.telegram_id == user_telegram_id)
    )
    me = result.scalar_one_or_none()
    all_users = friends + ([me] if me else [])
    all_users.sort(key=get_learning_streak_days, reverse=True)
    return [(u, i + 1) for i, u in enumerate(all_users)]


async def get_user_by_username(session: AsyncSession, username: str) -> User | None:
    """Поиск пользователя по @username (без @)."""
    clean = username.lstrip("@").lower()
    result = await session.execute(
        select(User).where(func.lower(User.username) == clean)
    )
    return result.scalar_one_or_none()


async def count_materials(session: AsyncSession, user_telegram_id: int) -> int:
    result = await session.execute(
        select(func.count()).where(Material.user_telegram_id == user_telegram_id)
    )
    return result.scalar() or 0


async def get_profile_overview(session: AsyncSession, user_telegram_id: int) -> ProfileOverview | None:
    user_result = await session.execute(
        select(User).where(User.telegram_id == user_telegram_id)
    )
    user = user_result.scalar_one_or_none()
    if user is None:
        return None

    subjects_result = await session.execute(
        select(func.count()).select_from(Subject).where(Subject.user_telegram_id == user_telegram_id)
    )
    materials_result = await session.execute(
        select(func.count()).select_from(Material).where(Material.user_telegram_id == user_telegram_id)
    )
    focus_result = await session.execute(
        select(
            func.count(PomodoroSessionLog.id),
            func.coalesce(func.sum(PomodoroSessionLog.work_minutes), 0),
        ).where(PomodoroSessionLog.user_telegram_id == user_telegram_id)
    )
    focus_sessions, focus_minutes = focus_result.one()
    friends = await get_friends(session, user_telegram_id)

    return ProfileOverview(
        user=user,
        subjects_count=int(subjects_result.scalar() or 0),
        materials_count=int(materials_result.scalar() or 0),
        friends_count=len(friends),
        total_focus_sessions=int(focus_sessions or 0),
        total_focus_minutes=int(focus_minutes or 0),
    )


async def get_statistics_overview(
    session: AsyncSession,
    user_telegram_id: int,
    period_key: str,
) -> StatisticsOverview:
    window = get_period_window(period_key)
    material_period = _in_period(Material.created_at, window)
    pomo_period = _in_period(PomodoroSessionLog.completed_at, window)
    deadline_period = _in_period(Deadline.due_at, window)

    mat_stmt = select(
        func.count(Material.id),
        func.count(func.distinct(Material.subject_id)),
    ).where(Material.user_telegram_id == user_telegram_id)
    if material_period is not None:
        mat_stmt = mat_stmt.where(material_period)
    materials_count, active_subjects = (await session.execute(mat_stmt)).one()

    focus_stmt = select(func.coalesce(func.sum(PomodoroSessionLog.work_minutes), 0)).where(
        PomodoroSessionLog.user_telegram_id == user_telegram_id
    )
    if pomo_period is not None:
        focus_stmt = focus_stmt.where(pomo_period)
    focus_minutes = (await session.execute(focus_stmt)).scalar() or 0

    deadlines_stmt = select(func.count(Deadline.id)).where(Deadline.user_telegram_id == user_telegram_id)
    if deadline_period is not None:
        deadlines_stmt = deadlines_stmt.where(deadline_period)
    deadlines_total = (await session.execute(deadlines_stmt)).scalar() or 0

    return StatisticsOverview(
        period=window,
        active_subjects=int(active_subjects or 0),
        materials_added=int(materials_count or 0),
        focus_minutes=int(focus_minutes or 0),
        deadlines_total=int(deadlines_total or 0),
    )


async def get_subject_progress_stats(
    session: AsyncSession,
    user_telegram_id: int,
    period_key: str,
) -> list[SubjectProgressItem]:
    window = get_period_window(period_key)

    totals_result = await session.execute(
        select(
            Subject.id,
            Subject.name,
            func.count(Material.id),
        )
        .select_from(Subject)
        .outerjoin(
            Material,
            and_(
                Material.subject_id == Subject.id,
                Material.user_telegram_id == user_telegram_id,
            ),
        )
        .where(Subject.user_telegram_id == user_telegram_id)
        .group_by(Subject.id, Subject.name)
        .order_by(Subject.name)
    )
    totals = {
        subject_id: (name, int(total_materials or 0))
        for subject_id, name, total_materials in totals_result.all()
    }
    if not totals:
        return []

    learned_stmt = select(
        Material.subject_id,
        func.count(Material.id),
    ).where(
        Material.user_telegram_id == user_telegram_id,
        Material.subject_id.is_not(None),
        Material.learned_at.is_not(None),
    ).group_by(Material.subject_id)
    learned_totals = {
        int(subject_id): int(learned_count or 0)
        for subject_id, learned_count in (await session.execute(learned_stmt)).all()
    }

    period_stats: dict[int, tuple[int, int]] = {}
    period_stmt = select(
        Material.subject_id,
        func.count(Material.id),
        func.count(
            func.distinct(
                func.date(func.coalesce(Material.learned_at, Material.created_at))
            )
        ),
    ).where(
        Material.user_telegram_id == user_telegram_id,
        Material.subject_id.is_not(None),
    )
    material_period = _in_period(func.coalesce(Material.learned_at, Material.created_at), window)
    if material_period is not None:
        period_stmt = period_stmt.where(material_period)
    period_stmt = period_stmt.group_by(Material.subject_id)
    for subject_id, materials_count, active_days in (await session.execute(period_stmt)).all():
        period_stats[int(subject_id)] = (int(materials_count or 0), int(active_days or 0))

    items = []
    for subject_id, (name, total_materials) in totals.items():
        period_materials, active_days = period_stats.get(subject_id, (0, 0))
        learned_materials = learned_totals.get(subject_id, 0)
        progress = 0 if total_materials == 0 else round(learned_materials / total_materials * 100)
        items.append(
            SubjectProgressItem(
                subject_id=subject_id,
                subject_name=name,
                total_materials=total_materials,
                learned_materials=learned_materials,
                period_materials=period_materials,
                active_days=active_days,
                progress_percent=progress,
            )
        )

    items.sort(key=lambda item: (-item.progress_percent, item.subject_name.lower()))
    return items


async def get_subject_detail_stats(
    session: AsyncSession,
    user_telegram_id: int,
    subject_id: int,
    period_key: str,
) -> SubjectProgressItem | None:
    for item in await get_subject_progress_stats(session, user_telegram_id, period_key):
        if item.subject_id == subject_id:
            return item
    return None


async def get_materials_statistics(
    session: AsyncSession,
    user_telegram_id: int,
    period_key: str,
) -> MaterialsStats:
    window = get_period_window(period_key)
    stmt = select(Material.material_type, func.count(Material.id)).where(
        Material.user_telegram_id == user_telegram_id
    )
    material_period = _in_period(Material.created_at, window)
    if material_period is not None:
        stmt = stmt.where(material_period)
    stmt = stmt.group_by(Material.material_type)

    grouped = {material_type: int(count or 0) for material_type, count in (await session.execute(stmt)).all()}
    total = sum(grouped.values())
    docs_and_pdfs = grouped.get(MATERIAL_TYPE_DOC, 0) + grouped.get(MATERIAL_TYPE_PDF, 0) + grouped.get(MATERIAL_TYPE_FILE, 0)
    links = grouped.get(MATERIAL_TYPE_LINK, 0)
    media = grouped.get(MATERIAL_TYPE_IMAGE, 0) + grouped.get(MATERIAL_TYPE_VIDEO, 0) + grouped.get(MATERIAL_TYPE_AUDIO, 0)
    archives = grouped.get(MATERIAL_TYPE_ARCHIVE, 0)
    other = total - docs_and_pdfs - links - media - archives

    return MaterialsStats(
        total=total,
        docs_and_pdfs=docs_and_pdfs,
        links=links,
        media=media,
        archives=archives,
        other=max(other, 0),
    )


async def get_deadline_statistics(
    session: AsyncSession,
    user_telegram_id: int,
    period_key: str,
) -> DeadlineStats:
    window = get_period_window(period_key)
    stmt = select(Deadline).where(Deadline.user_telegram_id == user_telegram_id)
    deadline_period = _in_period(Deadline.due_at, window)
    if deadline_period is not None:
        stmt = stmt.where(deadline_period)

    now = datetime.now(timezone.utc)
    deadlines = list((await session.execute(stmt)).scalars().all())

    completed_on_time = 0
    overdue = 0
    in_progress = 0
    for deadline in deadlines:
        if deadline.completed_at is not None:
            if deadline.completed_at <= deadline.due_at:
                completed_on_time += 1
            else:
                overdue += 1
            continue

        if deadline.due_at < now or deadline.status == "overdue":
            overdue += 1
        else:
            in_progress += 1

    return DeadlineStats(
        total=len(deadlines),
        completed_on_time=completed_on_time,
        overdue=overdue,
        in_progress=in_progress,
    )


async def get_activity_statistics(
    session: AsyncSession,
    user_telegram_id: int,
    period_key: str,
) -> ActivityStats:
    window = get_period_window(period_key)

    user_result = await session.execute(select(User).where(User.telegram_id == user_telegram_id))
    user = user_result.scalar_one_or_none()
    streak = get_learning_streak_days(user)

    material_stmt = select(
        func.count(Material.id),
        func.count(func.distinct(func.date(Material.created_at))),
    ).where(Material.user_telegram_id == user_telegram_id)
    material_period = _in_period(Material.created_at, window)
    if material_period is not None:
        material_stmt = material_stmt.where(material_period)
    materials_added, _material_days = (await session.execute(material_stmt)).one()

    pomo_stmt = select(
        func.count(PomodoroSessionLog.id),
        func.coalesce(func.sum(PomodoroSessionLog.work_minutes), 0),
        func.count(func.distinct(func.date(PomodoroSessionLog.completed_at))),
    ).where(PomodoroSessionLog.user_telegram_id == user_telegram_id)
    pomo_period = _in_period(PomodoroSessionLog.completed_at, window)
    if pomo_period is not None:
        pomo_stmt = pomo_stmt.where(pomo_period)
    pomo_sessions, focus_minutes, _pomo_days = (await session.execute(pomo_stmt)).one()

    # distinct days считаем как объединение дней с материалами и помодоро
    material_days_stmt = select(func.date(Material.created_at)).where(Material.user_telegram_id == user_telegram_id)
    if material_period is not None:
        material_days_stmt = material_days_stmt.where(material_period)
    pomo_days_stmt = select(func.date(PomodoroSessionLog.completed_at)).where(PomodoroSessionLog.user_telegram_id == user_telegram_id)
    if pomo_period is not None:
        pomo_days_stmt = pomo_days_stmt.where(pomo_period)
    quiz_period = _in_period(Material.learned_at, window)
    quiz_days_stmt = select(func.date(Material.learned_at)).where(
        Material.user_telegram_id == user_telegram_id,
        Material.learned_at.is_not(None),
    )
    if quiz_period is not None:
        quiz_days_stmt = quiz_days_stmt.where(quiz_period)
    material_dates = {row[0] for row in (await session.execute(material_days_stmt)).all()}
    pomo_dates = {row[0] for row in (await session.execute(pomo_days_stmt)).all()}
    quiz_dates = {row[0] for row in (await session.execute(quiz_days_stmt)).all()}
    active_days = len(material_dates | pomo_dates | quiz_dates)

    total_focus_minutes = int(focus_minutes or 0)
    average_focus_minutes = total_focus_minutes / active_days if active_days else 0.0

    return ActivityStats(
        active_days=active_days,
        current_streak=int(streak or 0),
        total_focus_minutes=total_focus_minutes,
        average_focus_minutes=average_focus_minutes,
        pomodoro_sessions=int(pomo_sessions or 0),
        materials_added=int(materials_added or 0),
    )


async def get_achievements_overview(
    session: AsyncSession,
    user_telegram_id: int,
) -> AchievementsOverview | None:
    profile = await get_profile_overview(session, user_telegram_id)
    if profile is None:
        return None

    materials = list(
        (
            await session.execute(
                select(Material).where(Material.user_telegram_id == user_telegram_id)
            )
        ).scalars().all()
    )
    deadlines = list(
        (
            await session.execute(
                select(Deadline).where(Deadline.user_telegram_id == user_telegram_id)
            )
        ).scalars().all()
    )
    pomo_logs = list(
        (
            await session.execute(
                select(PomodoroSessionLog).where(PomodoroSessionLog.user_telegram_id == user_telegram_id)
            )
        ).scalars().all()
    )

    activity_days = {m.created_at.date() for m in materials if m.created_at is not None}
    activity_days |= {p.completed_at.date() for p in pomo_logs if p.completed_at is not None}
    activity_days |= {m.learned_at.date() for m in materials if m.learned_at is not None}
    max_activity_streak = _max_consecutive_days(activity_days)
    current_test_streak = get_learning_streak_days(profile.user)

    docs_like_count = sum(
        1
        for item in materials
        if item.material_type in {MATERIAL_TYPE_DOC, MATERIAL_TYPE_PDF, MATERIAL_TYPE_FILE}
    )
    subjects_with_materials = {
        int(item.subject_id)
        for item in materials
        if item.subject_id is not None
    }

    planned_deadlines = sum(
        1
        for deadline in deadlines
        if deadline.created_at is not None
        and deadline.due_at is not None
        and (deadline.due_at - deadline.created_at).days >= 7
    )
    material_before_deadline = any(
        material.subject_id is not None
        and deadline.subject_id == material.subject_id
        and material.created_at is not None
        and deadline.due_at is not None
        and material.created_at <= deadline.due_at
        for material in materials
        for deadline in deadlines
    )

    overdue_deadlines = 0
    on_time_completed = 0
    early_completed = 0
    now = datetime.now(timezone.utc)
    for deadline in deadlines:
        if deadline.completed_at is not None:
            if deadline.completed_at <= deadline.due_at:
                on_time_completed += 1
                if deadline.completed_at <= deadline.due_at - timedelta(days=7):
                    early_completed += 1
            else:
                overdue_deadlines += 1
        elif deadline.due_at < now or deadline.status == "overdue":
            overdue_deadlines += 1

    on_time_streak = _on_time_deadline_streak(deadlines)

    discipline_items = [
        AchievementItem(
            title="Старт без хаоса",
            description="добавлено 10 предметов в боте",
            done=profile.subjects_count >= 10,
            current=profile.subjects_count,
            target=10,
        ),
        AchievementItem(
            title="Вовремя в системе",
            description="активность в боте минимум 5 дней подряд",
            done=max_activity_streak >= 5,
            current=max_activity_streak,
            target=5,
        ),
        AchievementItem(
            title="Планировщик",
            description="дедлайн добавлен заранее (минимум за 7 дней)",
            done=planned_deadlines >= 1,
            current=planned_deadlines,
            target=1,
        ),
        AchievementItem(
            title="Осознанное обучение",
            description="материалы загружены до начала дедлайна",
            done=material_before_deadline,
            current=1 if material_before_deadline else 0,
            target=1,
        ),
        AchievementItem(
            title="Системный студент",
            description="нет пропусков активности в течение 14 дней",
            done=max_activity_streak >= 14,
            current=max_activity_streak,
            target=14,
        ),
    ]

    deadline_items = [
        AchievementItem(
            title="Железная дисциплина",
            description="0 просроченных дедлайнов",
            done=len(deadlines) > 0 and overdue_deadlines == 0,
            current=max(0, len(deadlines) - overdue_deadlines),
            target=max(len(deadlines), 1),
        ),
        AchievementItem(
            title="Почти идеально",
            description="5 дедлайнов подряд сданы вовремя",
            done=on_time_streak >= 5,
            current=on_time_streak,
            target=5,
        ),
        AchievementItem(
            title="Мастер планирования",
            description="10 дедлайнов без опозданий",
            done=on_time_completed >= 10,
            current=on_time_completed,
            target=10,
        ),
        AchievementItem(
            title="Без паники",
            description="3 дедлайна закрыты за неделю до срока",
            done=early_completed >= 3,
            current=early_completed,
            target=3,
        ),
    ]

    materials_items = [
        AchievementItem(
            title="Первый шаг",
            description="загружен первый файл",
            done=profile.materials_count >= 1,
            current=profile.materials_count,
            target=1,
        ),
        AchievementItem(
            title="Организованный студент",
            description="загружено 10 учебных материалов",
            done=docs_like_count >= 10,
            current=docs_like_count,
            target=10,
        ),
        AchievementItem(
            title="Архивариус",
            description="загружено 30 файлов",
            done=profile.materials_count >= 30,
            current=profile.materials_count,
            target=30,
        ),
        AchievementItem(
            title="База знаний",
            description="файлы загружены по 10 предметам",
            done=len(subjects_with_materials) >= 10,
            current=len(subjects_with_materials),
            target=10,
        ),
    ]

    series_items = [
        AchievementItem(
            title="В ритме",
            description="3 дня подряд решать тесты",
            done=current_test_streak >= 3,
            current=current_test_streak,
            target=3,
        ),
        AchievementItem(
            title="Неделя без пропусков",
            description="7 дней подряд решать тесты",
            done=current_test_streak >= 7,
            current=current_test_streak,
            target=7,
        ),
        AchievementItem(
            title="Месяц фокуса",
            description="30 дней подряд решать тесты",
            done=current_test_streak >= 30,
            current=current_test_streak,
            target=30,
        ),
        AchievementItem(
            title="Легенда",
            description="60 дней подряд решать тесты",
            done=current_test_streak >= 60,
            current=current_test_streak,
            target=60,
        ),
    ]

    categories = [
        AchievementCategory(
            key="discipline",
            title="Учебная дисциплина",
            intro="Эти достижения показывают, насколько стабильно и осознанно ты подходишь к учёбе.",
            items=discipline_items,
        ),
        AchievementCategory(
            key="deadlines",
            title="Дедлайны",
            intro="Эти достижения показывают, насколько ты умеешь планировать время.",
            items=deadline_items,
        ),
        AchievementCategory(
            key="materials",
            title="Материалы",
            intro="Чем больше ты систематизируешь учёбу — тем выше твой уровень.",
            items=materials_items,
        ),
        AchievementCategory(
            key="series",
            title="Серии",
            intro="Регулярность — ключ к результату.",
            items=series_items,
        ),
    ]

    total_count = sum(len(category.items) for category in categories)
    unlocked_count = sum(item.done for category in categories for item in category.items)
    return AchievementsOverview(
        unlocked_count=int(unlocked_count),
        total_count=total_count,
        categories=categories,
    )
