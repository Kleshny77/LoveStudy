# флоу загрузки: инструкция → файл → выбор/создание папки → готово
#
# Поддерживаемые типы: файлы любого формата (pdf, docx, zip, фото, видео, архивы...)
#
# Архитектурные гарантии:
#   1. ConversationHandler зарегистрирован ПЕРВЫМ — не конкурирует с глобальными хендлерами
#   2. answer() вызывается первым на любой callback — убираем спиннер даже при ошибке
#   3. Все обращения к БД обёрнуты в try/except — краш в БД не роняет бота
#   4. При недоступной БД показываем папку "только создать" — не теряем пользователя
#   5. fallbacks завершают диалог при /start или CB_MAT_CANCEL из любого состояния

import logging
import warnings

from telegram import Update
from telegram.warnings import PTBUserWarning
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from constants import (
    CB_MAT_CANCEL,
    CB_MAT_CREATE,
    CB_MAT_FOLDER_PREFIX,
    CB_MAT_MORE,
    CB_MAT_TO_MAIN,
    CB_MAIN_UPLOAD,
    CB_SUB_ADD,
    MAX_FILE_SIZE_MB,
    ST_CHOOSE_FOLDER,
    ST_ENTER_FOLDER,
    ST_INSTRUCTIONS,
    UD_FILE_ID,
    UD_FILE_NAME,
    UD_FILE_SIZE,
    UD_FILE_UNIQUE,
    UD_MIME_TYPE,
    UD_TARGET_SUBJECT_ID,
    UD_TARGET_SUBJECT_NAME,
)
from db.repositories import (
    get_or_create_user,
    get_subject_by_id,
    get_user_subjects,
    save_file_to_new_subject,
    save_file_to_subject,
)
from services.main_menu import get_main_menu_keyboard, get_main_menu_text
from services.material_upload import (
    get_db_error_text,
    get_done_keyboard,
    get_done_text,
    get_enter_folder_name_keyboard,
    get_enter_folder_name_text,
    get_file_too_big_text,
    get_folder_choice_keyboard,
    get_folder_choice_text,
    get_instructions_keyboard,
    get_instructions_text,
    get_no_db_text,
)
from services.subject_detail import (
    get_add_done_keyboard,
    get_add_done_text,
    get_add_to_subject_keyboard,
    get_add_to_subject_text,
)

warnings.filterwarnings("ignore", message=r"If 'per_message=False'", category=PTBUserWarning)

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# Утилиты
# ──────────────────────────────────────────────

def _uid(update: Update) -> int:
    return update.effective_user.id  # type: ignore[union-attr]


def _name(update: Update) -> str | None:
    user = update.effective_user
    return user.first_name if user else None


def _factory(context: ContextTypes.DEFAULT_TYPE):
    return context.bot_data.get("session_factory")


async def _get_subjects(context: ContextTypes.DEFAULT_TYPE, uid: int) -> list[tuple[int, str]]:
    """Возвращает список папок пользователя. При ошибке БД — пустой список."""
    factory = _factory(context)
    if not factory:
        return []
    try:
        async with factory() as session:
            return await get_user_subjects(session, uid)
    except Exception:
        logger.exception("Ошибка при получении списка предметов (uid=%s)", uid)
        return []


def _clear_ud(context: ContextTypes.DEFAULT_TYPE) -> None:
    for key in (
        UD_FILE_ID, UD_FILE_NAME, UD_FILE_SIZE, UD_FILE_UNIQUE,
        UD_MIME_TYPE, UD_TARGET_SUBJECT_ID, UD_TARGET_SUBJECT_NAME,
    ):
        context.user_data.pop(key, None)


# ──────────────────────────────────────────────
# Вход в флоу
# ──────────────────────────────────────────────

async def enter_instructions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    _clear_ud(context)
    await query.edit_message_text(
        get_instructions_text(),
        reply_markup=get_instructions_keyboard(),
        parse_mode="HTML",
    )
    return ST_INSTRUCTIONS


async def enter_add_to_subject(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Вход в флоу 'Добавить файл' из просмотра конкретной папки."""
    query = update.callback_query
    await query.answer()
    _clear_ud(context)

    subject_id = int(query.data.removeprefix(CB_SUB_ADD))
    uid = _uid(update)

    # Получаем имя папки
    factory = _factory(context)
    subject_name = "папку"
    if factory:
        try:
            async with factory() as session:
                from db.repositories import get_subject_by_id
                subj = await get_subject_by_id(session, subject_id, uid)
                if subj:
                    subject_name = subj.name
        except Exception:
            logger.exception("Ошибка при получении имени папки (subject_id=%s)", subject_id)

    context.user_data[UD_TARGET_SUBJECT_ID]   = subject_id
    context.user_data[UD_TARGET_SUBJECT_NAME] = subject_name

    await query.edit_message_text(
        get_add_to_subject_text(subject_name),
        reply_markup=get_add_to_subject_keyboard(),
        parse_mode="HTML",
    )
    return ST_INSTRUCTIONS


# ──────────────────────────────────────────────
# STATE: ST_INSTRUCTIONS — ждём файл или ссылку
# ──────────────────────────────────────────────

async def _save_to_target_subject(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> int:
    """Сохраняет файл/ссылку сразу в целевую папку (если задана через UD_TARGET_SUBJECT_ID)."""
    uid = _uid(update)
    subject_id   = context.user_data[UD_TARGET_SUBJECT_ID]
    subject_name = context.user_data.get(UD_TARGET_SUBJECT_NAME, "папку")
    factory = _factory(context)

    if not factory:
        await update.message.reply_text(get_no_db_text(), parse_mode="HTML")
        return ConversationHandler.END

    try:
        async with factory() as session:
            await get_or_create_user(
                session, uid,
                update.effective_user.username,
                update.effective_user.first_name,
            )
            await save_file_to_subject(
                session,
                user_telegram_id=uid,
                subject_id=subject_id,
                subject_name=subject_name,
                telegram_file_id=context.user_data[UD_FILE_ID],
                file_unique_id=context.user_data.get(UD_FILE_UNIQUE, ""),
                original_filename=context.user_data.get(UD_FILE_NAME),
                file_size=context.user_data.get(UD_FILE_SIZE),
                mime_type=context.user_data.get(UD_MIME_TYPE),
            )
            file_label = context.user_data.get(UD_FILE_NAME, "файл")
    except Exception:
        logger.exception("Ошибка при сохранении в папку (uid=%s, subject_id=%s)", uid, subject_id)
        await update.message.reply_text(get_db_error_text(), reply_markup=get_done_keyboard(), parse_mode="HTML")
        return ConversationHandler.END

    await update.message.reply_text(
        get_add_done_text(file_label, subject_name),
        reply_markup=get_add_done_keyboard(subject_id),
        parse_mode="HTML",
    )
    return ConversationHandler.END


def _store_media_ud(
    context: ContextTypes.DEFAULT_TYPE,
    file_id: str,
    file_unique_id: str,
    file_name: str,
    file_size: int,
    mime_type: str | None,
) -> None:
    context.user_data[UD_FILE_ID]     = file_id
    context.user_data[UD_FILE_UNIQUE] = file_unique_id
    context.user_data[UD_FILE_NAME]   = file_name
    context.user_data[UD_FILE_SIZE]   = file_size
    context.user_data[UD_MIME_TYPE]   = mime_type


async def _after_media_stored(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> int:
    """Общая логика после сохранения медиа в user_data: проверяем target или показываем выбор папки."""
    if context.user_data.get(UD_TARGET_SUBJECT_ID):
        return await _save_to_target_subject(update, context)

    uid = _uid(update)
    factory = _factory(context)
    if factory:
        try:
            async with factory() as session:
                await get_or_create_user(
                    session, uid,
                    update.effective_user.username,
                    update.effective_user.first_name,
                )
        except Exception:
            logger.exception("Ошибка при get_or_create_user (uid=%s)", uid)

    subjects = await _get_subjects(context, uid)
    label = context.user_data[UD_FILE_NAME]
    await update.message.reply_text(
        get_folder_choice_text(label),
        reply_markup=get_folder_choice_keyboard(subjects),
        parse_mode="HTML",
    )
    return ST_CHOOSE_FOLDER


async def on_file_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Файл отправлен как документ (оригинальное качество)."""
    doc = update.message.document
    file_size_bytes = doc.file_size or 0

    if file_size_bytes / (1024 * 1024) > MAX_FILE_SIZE_MB:
        await update.message.reply_text(
            get_file_too_big_text(file_size_bytes / (1024 * 1024)),
            reply_markup=get_instructions_keyboard(),
        )
        return ST_INSTRUCTIONS

    _store_media_ud(context, doc.file_id, doc.file_unique_id,
                    doc.file_name or "файл", file_size_bytes, doc.mime_type)
    return await _after_media_stored(update, context)


async def on_photo_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Фото отправлено сжатым (не как документ). Берём максимальное разрешение."""
    photo = update.message.photo[-1]  # последний = наибольший размер
    file_size_bytes = photo.file_size or 0

    if file_size_bytes / (1024 * 1024) > MAX_FILE_SIZE_MB:
        await update.message.reply_text(
            get_file_too_big_text(file_size_bytes / (1024 * 1024)),
            reply_markup=get_instructions_keyboard(),
        )
        return ST_INSTRUCTIONS

    # Генерируем имя файла на основе даты сообщения
    from datetime import datetime
    ts = update.message.date.strftime("%Y%m%d_%H%M%S") if update.message.date else "photo"
    _store_media_ud(context, photo.file_id, photo.file_unique_id,
                    f"photo_{ts}.jpg", file_size_bytes, "image/jpeg")
    return await _after_media_stored(update, context)


async def on_video_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Видео отправлено сжатым (не как документ)."""
    video = update.message.video
    file_size_bytes = video.file_size or 0

    if file_size_bytes / (1024 * 1024) > MAX_FILE_SIZE_MB:
        await update.message.reply_text(
            get_file_too_big_text(file_size_bytes / (1024 * 1024)),
            reply_markup=get_instructions_keyboard(),
        )
        return ST_INSTRUCTIONS

    from datetime import datetime
    ts = update.message.date.strftime("%Y%m%d_%H%M%S") if update.message.date else "video"
    name = video.file_name or f"video_{ts}.mp4"
    _store_media_ud(context, video.file_id, video.file_unique_id,
                    name, file_size_bytes, video.mime_type or "video/mp4")
    return await _after_media_stored(update, context)


async def on_text_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "Некорректный формат материала. Пришли файл, фото или видео.",
        reply_markup=get_instructions_keyboard(),
    )
    return ST_INSTRUCTIONS


# ──────────────────────────────────────────────
# STATE: ST_CHOOSE_FOLDER
# ──────────────────────────────────────────────

async def on_folder_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    subject_id = int(query.data.removeprefix(CB_MAT_FOLDER_PREFIX))
    uid = _uid(update)

    factory = _factory(context)
    if not factory:
        await query.edit_message_text(get_no_db_text(), parse_mode="HTML")
        return ConversationHandler.END

    try:
        async with factory() as session:
            subject = await get_subject_by_id(session, subject_id, uid)
            if not subject:
                await query.edit_message_text("Папка не найдена. Попробуй ещё раз.")
                return ST_CHOOSE_FOLDER

            await save_file_to_subject(
                session,
                user_telegram_id=uid,
                subject_id=subject.id,
                subject_name=subject.name,
                telegram_file_id=context.user_data[UD_FILE_ID],
                file_unique_id=context.user_data.get(UD_FILE_UNIQUE, ""),
                original_filename=context.user_data.get(UD_FILE_NAME),
                file_size=context.user_data.get(UD_FILE_SIZE),
                mime_type=context.user_data.get(UD_MIME_TYPE),
            )
            folder_name = subject.name
            saved_subject_id = subject.id
    except Exception:
        logger.exception("Ошибка при сохранении материала (uid=%s)", uid)
        await query.edit_message_text(get_db_error_text(), reply_markup=get_done_keyboard(), parse_mode="HTML")
        return ConversationHandler.END

    await query.edit_message_text(
        get_done_text(folder_name, is_new_folder=False),
        reply_markup=get_done_keyboard(subject_id=saved_subject_id),
        parse_mode="HTML",
    )
    return ConversationHandler.END


async def on_create_folder(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        get_enter_folder_name_text(),
        reply_markup=get_enter_folder_name_keyboard(),
    )
    return ST_ENTER_FOLDER


# ──────────────────────────────────────────────
# STATE: ST_ENTER_FOLDER
# ──────────────────────────────────────────────

async def on_folder_name_entered(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    folder_name = update.message.text.strip()
    if not folder_name:
        await update.message.reply_text(
            get_enter_folder_name_text(),
            reply_markup=get_enter_folder_name_keyboard(),
        )
        return ST_ENTER_FOLDER

    uid = _uid(update)
    factory = _factory(context)
    if not factory:
        await update.message.reply_text(get_no_db_text(), parse_mode="HTML")
        return ConversationHandler.END

    saved_subject_id = None
    try:
        async with factory() as session:
            await get_or_create_user(
                session, uid,
                update.effective_user.username,
                update.effective_user.first_name,
            )
            mat = await save_file_to_new_subject(
                session,
                user_telegram_id=uid,
                subject_name=folder_name,
                telegram_file_id=context.user_data[UD_FILE_ID],
                file_unique_id=context.user_data.get(UD_FILE_UNIQUE, ""),
                original_filename=context.user_data.get(UD_FILE_NAME),
                file_size=context.user_data.get(UD_FILE_SIZE),
                mime_type=context.user_data.get(UD_MIME_TYPE),
            )
            saved_subject_id = mat.subject_id
    except Exception:
        logger.exception("Ошибка при сохранении в новую папку (uid=%s)", uid)
        await update.message.reply_text(get_db_error_text(), reply_markup=get_done_keyboard(), parse_mode="HTML")
        return ConversationHandler.END

    await update.message.reply_text(
        get_done_text(folder_name, is_new_folder=True),
        reply_markup=get_done_keyboard(subject_id=saved_subject_id),
        parse_mode="HTML",
    )
    return ConversationHandler.END


# ──────────────────────────────────────────────
# Fallbacks: выход из диалога
# ──────────────────────────────────────────────

async def fallback_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """← Назад: из загрузки возвращаемся туда, откуда пришли."""
    query = update.callback_query
    await query.answer()
    target_subject_id = context.user_data.get(UD_TARGET_SUBJECT_ID)
    _clear_ud(context)
    if target_subject_id:
        from handlers.subjects import _show_subject_detail
        await _show_subject_detail(update, context, target_subject_id, page=1)
    else:
        from services.main_menu import get_materials_hub_keyboard, get_materials_hub_text
        await query.edit_message_text(
            get_materials_hub_text(),
            reply_markup=get_materials_hub_keyboard(),
            parse_mode="HTML",
        )
    return ConversationHandler.END


async def fallback_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """🏠 Главное меню из любого состояния загрузки."""
    query = update.callback_query
    await query.answer()
    _clear_ud(context)
    await query.edit_message_text(
        get_main_menu_text(_name(update)),
        reply_markup=get_main_menu_keyboard(),
        parse_mode="HTML",
    )
    return ConversationHandler.END


async def fallback_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    _clear_ud(context)
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=get_main_menu_text(_name(update)),
        reply_markup=get_main_menu_keyboard(),
        parse_mode="HTML",
    )
    return ConversationHandler.END


# ──────────────────────────────────────────────
# Регистрация
# ──────────────────────────────────────────────

def register(app: Application) -> None:
    conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(enter_instructions, pattern=rf"^({CB_MAIN_UPLOAD}|{CB_MAT_MORE})$"),
            CallbackQueryHandler(enter_add_to_subject, pattern=rf"^{CB_SUB_ADD}\d+$"),
        ],
        states={
            ST_INSTRUCTIONS: [
                MessageHandler(filters.Document.ALL, on_file_received),
                MessageHandler(filters.PHOTO, on_photo_received),
                MessageHandler(filters.VIDEO, on_video_received),
                MessageHandler(filters.TEXT & ~filters.COMMAND, on_text_received),
            ],
            ST_CHOOSE_FOLDER: [
                CallbackQueryHandler(on_folder_chosen, pattern=rf"^{CB_MAT_FOLDER_PREFIX}\d+$"),
                CallbackQueryHandler(on_create_folder, pattern=rf"^{CB_MAT_CREATE}$"),
            ],
            ST_ENTER_FOLDER: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, on_folder_name_entered),
            ],
        },
        fallbacks=[
            CallbackQueryHandler(fallback_cancel, pattern=rf"^{CB_MAT_CANCEL}$"),
            CallbackQueryHandler(fallback_to_main, pattern=rf"^{CB_MAT_TO_MAIN}$"),
            CommandHandler("start", fallback_start),
        ],
        per_user=True,
        per_chat=True,
        conversation_timeout=1800,  # 30 минут бездействия → автозакрытие
    )

    app.add_handler(conv)
