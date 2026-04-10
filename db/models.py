# модели БД: пользователь, предмет, материал, настройки помодоро

from sqlalchemy import BigInteger, Boolean, Column, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    telegram_id        = Column(BigInteger, primary_key=True)
    username           = Column(String(255), nullable=True)
    first_name         = Column(String(255), nullable=True)
    created_at         = Column(DateTime(timezone=True), server_default=func.now())
    streak_days        = Column(Integer, nullable=False, default=0)
    last_activity_date = Column(Date, nullable=True)
    quiz_correct_answers = Column(Integer, nullable=False, default=0)
    quiz_wrong_answers   = Column(Integer, nullable=False, default=0)
    quiz_generations_today = Column(Integer, nullable=False, default=0)
    quiz_generations_date  = Column(Date, nullable=True)
    subscription_expires_at = Column(DateTime(timezone=True), nullable=True)
    subscription_provider_charge_id = Column(String(255), nullable=True)
    subscription_telegram_charge_id = Column(String(255), nullable=True)
    # Первый зафиксированный канал: ref_* из /start или "invite" при invite_-ссылке
    acquisition_ref = Column(String(128), nullable=True)


class TelegramUXSettings(Base):
    __tablename__ = "telegram_ux_settings"

    user_telegram_id      = Column(BigInteger, ForeignKey("users.telegram_id", ondelete="CASCADE"), primary_key=True)
    study_chat_id         = Column(BigInteger, nullable=True)
    study_chat_title      = Column(String(255), nullable=True)
    study_chat_username   = Column(String(255), nullable=True)
    focus_buddy_id        = Column(BigInteger, nullable=True)
    focus_buddy_name      = Column(String(255), nullable=True)
    focus_buddy_username  = Column(String(255), nullable=True)
    focus_buddy_enabled   = Column(Boolean, nullable=False, default=False)


class Friendship(Base):
    """Дружба между двумя пользователями. Хранится одна запись на пару:
    user1_id < user2_id (уникальность через UniqueConstraint)."""
    __tablename__ = "friendships"

    id         = Column(BigInteger, primary_key=True, autoincrement=True)
    user1_id   = Column(BigInteger, ForeignKey("users.telegram_id", ondelete="CASCADE"), nullable=False)
    user2_id   = Column(BigInteger, ForeignKey("users.telegram_id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (UniqueConstraint("user1_id", "user2_id", name="uq_friendship"),)


class Deadline(Base):
    __tablename__ = "deadlines"

    id               = Column(BigInteger, primary_key=True, autoincrement=True)
    user_telegram_id = Column(BigInteger, ForeignKey("users.telegram_id", ondelete="CASCADE"), nullable=False)
    subject_id       = Column(BigInteger, ForeignKey("subjects.id", ondelete="SET NULL"), nullable=True)
    title            = Column(String(255), nullable=False)
    status           = Column(String(32), nullable=False, default="open")
    due_at           = Column(DateTime(timezone=True), nullable=False)
    reminder_offset_minutes = Column(Integer, nullable=True)
    reminder_sent_at        = Column(DateTime(timezone=True), nullable=True)
    completed_at     = Column(DateTime(timezone=True), nullable=True)
    created_at       = Column(DateTime(timezone=True), server_default=func.now())


class DeadlineSettings(Base):
    __tablename__ = "deadline_settings"

    user_telegram_id       = Column(BigInteger, ForeignKey("users.telegram_id", ondelete="CASCADE"), primary_key=True)
    reminders_enabled      = Column(Boolean, nullable=False, default=True)
    daily_digest_enabled   = Column(Boolean, nullable=False, default=False)
    daily_digest_time      = Column(String(5), nullable=False, default="20:00")
    last_daily_digest_date = Column(Date, nullable=True)


class Subject(Base):
    __tablename__ = "subjects"

    id               = Column(BigInteger, primary_key=True, autoincrement=True)
    user_telegram_id = Column(BigInteger, ForeignKey("users.telegram_id", ondelete="CASCADE"), nullable=False)
    name             = Column(String(255), nullable=False)
    created_at       = Column(DateTime(timezone=True), server_default=func.now())


class Material(Base):
    """Единица хранения: файл любого формата ИЛИ ссылка.

    Для файлов:
      - telegram_file_id   — ID файла в Telegram (для скачивания)
      - file_unique_id     — стабильный глобальный ID (дедупликация)
      - original_filename  — оригинальное имя файла
      - file_size          — размер в байтах
      - mime_type          — MIME-тип из Telegram

    Для ссылок:
      - url               — полный URL
      - original_filename — заголовок/описание ссылки (необязательно)
      telegram_file_id / file_unique_id / file_size / mime_type = NULL

    material_type: "Файл" | "Архив" | "Изображение" | "Ссылка" | "PDF" | "Видео" | "Аудио" | "Документ"
    """
    __tablename__ = "materials"

    id               = Column(BigInteger, primary_key=True, autoincrement=True)
    user_telegram_id = Column(BigInteger, ForeignKey("users.telegram_id", ondelete="CASCADE"), nullable=False)
    subject_id       = Column(BigInteger, ForeignKey("subjects.id", ondelete="SET NULL"), nullable=True)
    subject_name     = Column(String(255), nullable=False)
    material_type    = Column(String(64), nullable=False, default="Файл")

    # --- файловые поля (NULL для ссылок) ---
    telegram_file_id  = Column(String(512), nullable=True)
    file_unique_id    = Column(String(512), nullable=True)   # глобально-стабильный ID Telegram
    original_filename = Column(String(512), nullable=True)
    file_size         = Column(BigInteger, nullable=True)    # байты
    mime_type         = Column(String(128), nullable=True)

    # --- поле для ссылок (NULL для файлов) ---
    url = Column(Text, nullable=True)

    year        = Column(String(16), nullable=True)
    description = Column(Text, nullable=True)
    quiz_correct_answers = Column(Integer, nullable=False, default=0)
    quiz_wrong_answers   = Column(Integer, nullable=False, default=0)
    learned_at  = Column(DateTime(timezone=True), nullable=True)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())


class PomodoroSettings(Base):
    """Настройки помодоро и счётчик сессий (по одной строке на пользователя)."""
    __tablename__ = "pomodoro_settings"

    user_telegram_id  = Column(BigInteger, ForeignKey("users.telegram_id", ondelete="CASCADE"), primary_key=True)
    work_minutes      = Column(Integer, nullable=False, default=25)
    break_minutes     = Column(Integer, nullable=False, default=5)
    sound_enabled     = Column(Boolean, nullable=False, default=True)
    reminder_enabled  = Column(Boolean, nullable=False, default=True)
    auto_break        = Column(Boolean, nullable=False, default=True)
    sessions_today    = Column(Integer, nullable=False, default=0)
    last_session_date = Column(Date, nullable=True)


class PomodoroSessionLog(Base):
    __tablename__ = "pomodoro_session_logs"

    id               = Column(BigInteger, primary_key=True, autoincrement=True)
    user_telegram_id = Column(BigInteger, ForeignKey("users.telegram_id", ondelete="CASCADE"), nullable=False)
    work_minutes     = Column(Integer, nullable=False, default=25)
    completed_at     = Column(DateTime(timezone=True), server_default=func.now())


class AnalyticsEvent(Base):
    """События продукта для дашбордов (Metabase / DataLens и т.д.)."""

    __tablename__ = "analytics_events"

    id               = Column(BigInteger, primary_key=True, autoincrement=True)
    user_telegram_id = Column(BigInteger, nullable=True, index=True)
    event_name       = Column(String(128), nullable=False, index=True)
    properties       = Column(JSONB, nullable=True)
    created_at       = Column(DateTime(timezone=True), server_default=func.now(), index=True)
