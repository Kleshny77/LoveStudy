# хендлеры для экранов: список предметов, просмотр предмета, файл, удаление

import logging
import math

from telegram import Update
from telegram.ext import Application, CallbackQueryHandler, ContextTypes

from constants import (
    CB_FILE_BACK,
    CB_FILE_TEST,
    CB_MAT_DEL,
    CB_MAT_DEL_N,
    CB_MAT_DEL_Y,
    CB_MAT_VIEW,
    CB_SUB_BACK,
    CB_SUB_DEL,
    CB_SUB_DEL_N,
    CB_SUB_DEL_Y,
    CB_SUB_PAGE,
    CB_SUB_TEST,
    CB_SUB_VIEW,
    MATERIALS_PER_PAGE,
    UD_VIEWING_MATERIAL_ID,
    UD_VIEWING_SUBJECT_ID,
    UD_VIEWING_SUBJECT_NAME,
)
from db.models import Material
from db.repositories import (
    delete_material,
    delete_subject,
    get_material_by_id,
    get_materials_by_subject,
    get_subject_by_id,
    get_user_subjects,
)
from services.subject_detail import (
    get_add_to_subject_text,
    get_deleted_text,
    get_delete_confirm_keyboard,
    get_delete_confirm_text,
    get_file_detail_keyboard,
    get_file_link_text,
    get_subject_delete_confirm_keyboard,
    get_subject_delete_confirm_text,
    get_subject_deleted_text,
    get_subject_detail_keyboard,
    get_subject_detail_text,
    get_subjects_list_keyboard,
    get_subjects_list_text,
)

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# Список предметов
# ──────────────────────────────────────────────

async def send_subjects_screen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает список предметов. Вызывается из main_menu handler."""
    session_factory = context.bot_data.get("session_factory")
    uid = update.effective_user.id

    subjects: list[tuple[int, str]] = []
    if session_factory:
        try:
            async with session_factory() as session:
                subjects = await get_user_subjects(session, uid)
        except Exception:
            logger.exception("Ошибка при загрузке предметов")

    text = get_subjects_list_text(len(subjects))
    keyboard = get_subjects_list_keyboard(subjects)

    query = update.callback_query
    if query:
        await query.edit_message_text(text, reply_markup=keyboard, parse_mode="HTML")
    else:
        await update.message.reply_text(text, reply_markup=keyboard, parse_mode="HTML")


# ──────────────────────────────────────────────
# Детали предмета
# ──────────────────────────────────────────────

async def _show_subject_detail(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    subject_id: int,
    page: int = 1,
) -> None:
    """Редактирует текущее сообщение, показывая детали предмета."""
    session_factory = context.bot_data.get("session_factory")
    uid = update.effective_user.id
    query = update.callback_query

    subject = None
    materials: list[Material] = []

    if session_factory:
        try:
            async with session_factory() as session:
                subject = await get_subject_by_id(session, subject_id, uid)
                if subject:
                    materials = await get_materials_by_subject(session, subject_id, uid)
        except Exception:
            logger.exception("Ошибка при загрузке предмета %s", subject_id)

    if not subject:
        await query.answer("Предмет не найден.", show_alert=True)
        return

    context.user_data[UD_VIEWING_SUBJECT_ID] = subject_id
    context.user_data[UD_VIEWING_SUBJECT_NAME] = subject.name

    total_pages = max(1, math.ceil(len(materials) / MATERIALS_PER_PAGE))
    page = max(1, min(page, total_pages))

    learned_count = sum(1 for material in materials if material.learned_at is not None)
    text = get_subject_detail_text(subject.name, materials, learned_count, page, total_pages)
    keyboard = get_subject_detail_keyboard(materials, subject_id, page, total_pages)

    await query.edit_message_text(text, reply_markup=keyboard, parse_mode="HTML")


async def on_subject_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    subject_id = int(query.data.removeprefix(CB_SUB_VIEW))
    await _show_subject_detail(update, context, subject_id, page=1)


async def on_page_changed(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    # формат: sub:pg:<subject_id>:<page>
    payload = query.data.removeprefix(CB_SUB_PAGE)
    parts = payload.split(":")
    if len(parts) != 2:
        return
    subject_id, page = int(parts[0]), int(parts[1])
    await _show_subject_detail(update, context, subject_id, page=page)


async def on_back_to_subject(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Возврат к текущему предмету (из детали файла или удаления)."""
    query = update.callback_query
    await query.answer()
    subject_id = context.user_data.get(UD_VIEWING_SUBJECT_ID)
    if not subject_id:
        from services.main_menu import get_materials_hub_keyboard, get_materials_hub_text
        await query.edit_message_text(
            get_materials_hub_text(),
            reply_markup=get_materials_hub_keyboard(),
            parse_mode="HTML",
        )
        return

    # Сообщения с медиа (документ, фото, видео) нельзя редактировать в текст —
    # убираем кнопки и отправляем детали предмета новым сообщением.
    msg = query.message
    is_media = bool(msg and (msg.document or msg.photo or msg.video or msg.audio or msg.voice))
    if is_media:
        try:
            await query.edit_message_reply_markup(reply_markup=None)
        except Exception:
            pass
        await _show_subject_detail_as_new(update, context, subject_id)
    else:
        await _show_subject_detail(update, context, subject_id, page=1)


# ──────────────────────────────────────────────
# Детали файла
# ──────────────────────────────────────────────

async def on_material_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправляет файл/ссылку и кнопки действий."""
    query = update.callback_query
    await query.answer()
    uid = update.effective_user.id
    material_id = int(query.data.removeprefix(CB_MAT_VIEW))
    session_factory = context.bot_data.get("session_factory")

    material = None
    if session_factory:
        try:
            async with session_factory() as session:
                material = await get_material_by_id(session, material_id, uid)
        except Exception:
            logger.exception("Ошибка при загрузке материала %s", material_id)

    if not material:
        await query.answer("Файл не найден.", show_alert=True)
        return

    context.user_data[UD_VIEWING_MATERIAL_ID] = material_id
    keyboard = get_file_detail_keyboard()

    if material.material_type == "Ссылка":
        url = material.url or ""
        text = get_file_link_text(url, material.original_filename)
        await query.message.reply_text(text, reply_markup=keyboard, parse_mode="HTML")
    else:
        file_id = material.telegram_file_id
        if not file_id:
            await query.answer("Файл недоступен.", show_alert=True)
            return
        if material.material_type == "Изображение":
            await query.message.reply_photo(
                photo=file_id,
                reply_markup=keyboard,
            )
        elif material.material_type == "Видео":
            await query.message.reply_video(
                video=file_id,
                reply_markup=keyboard,
            )
        elif material.material_type == "Аудио":
            await query.message.reply_audio(
                audio=file_id,
                reply_markup=keyboard,
            )
        else:
            await query.message.reply_document(
                document=file_id,
                reply_markup=keyboard,
            )


async def on_back_to_file(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Возврат к файлу с подтверждения удаления."""
    query = update.callback_query
    await query.answer()
    uid = update.effective_user.id
    material_id = context.user_data.get(UD_VIEWING_MATERIAL_ID)
    if not material_id:
        await on_back_to_subject(update, context)
        return

    session_factory = context.bot_data.get("session_factory")
    material = None
    if session_factory:
        try:
            async with session_factory() as session:
                material = await get_material_by_id(session, material_id, uid)
        except Exception:
            logger.exception("Ошибка при загрузке материала %s для возврата", material_id)

    if not material:
        await on_back_to_subject(update, context)
        return

    keyboard = get_file_detail_keyboard()
    if material.material_type == "Ссылка":
        url = material.url or ""
        text = get_file_link_text(url, material.original_filename)
        await query.edit_message_text(text, reply_markup=keyboard, parse_mode="HTML")
    else:
        # нельзя отредактировать файл в текст, поэтому редактируем только кнопки
        try:
            await query.edit_message_reply_markup(reply_markup=keyboard)
        except Exception:
            await query.message.reply_text(
                material.original_filename or "файл",
                reply_markup=keyboard,
            )


# ──────────────────────────────────────────────
# Удаление материала
# ──────────────────────────────────────────────

async def on_delete_material(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает подтверждение удаления."""
    query = update.callback_query
    await query.answer()
    uid = update.effective_user.id
    material_id = context.user_data.get(UD_VIEWING_MATERIAL_ID)
    if not material_id:
        await query.answer("Не удалось определить файл.", show_alert=True)
        return

    session_factory = context.bot_data.get("session_factory")
    name = "файл"
    if session_factory:
        try:
            async with session_factory() as session:
                m = await get_material_by_id(session, material_id, uid)
                if m:
                    name = m.original_filename or m.url or "файл"
        except Exception:
            logger.exception("Ошибка при загрузке имени материала для удаления")

    text = get_delete_confirm_text(name)
    keyboard = get_delete_confirm_keyboard()
    # отправляем новым сообщением, файловое сообщение нельзя редактировать в текст
    await query.message.reply_text(text, reply_markup=keyboard, parse_mode="HTML")


async def on_delete_confirmed(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    uid = update.effective_user.id
    material_id = context.user_data.get(UD_VIEWING_MATERIAL_ID)
    if not material_id:
        await query.answer("Не удалось определить файл.", show_alert=True)
        return

    session_factory = context.bot_data.get("session_factory")
    deleted = False
    name = "файл"
    if session_factory:
        try:
            async with session_factory() as session:
                m = await get_material_by_id(session, material_id, uid)
                if m:
                    name = m.original_filename or m.url or "файл"
                deleted = await delete_material(session, material_id, uid)
        except Exception:
            logger.exception("Ошибка при удалении материала %s", material_id)
            await query.edit_message_text("⚠️ Не удалось удалить файл. Попробуй ещё раз.")
            return

    if deleted:
        context.user_data.pop(UD_VIEWING_MATERIAL_ID, None)
        await query.edit_message_text(get_deleted_text(name), parse_mode="HTML")
        # показываем обновлённый предмет
        subject_id = context.user_data.get(UD_VIEWING_SUBJECT_ID)
        if subject_id:
            await _show_subject_detail_as_new(update, context, subject_id)
    else:
        await query.edit_message_text("⚠️ Файл не найден или уже удалён.")


async def _show_subject_detail_as_new(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    subject_id: int,
) -> None:
    """Отправляет детали предмета новым сообщением (используется после удаления файла)."""
    session_factory = context.bot_data.get("session_factory")
    uid = update.effective_user.id

    subject = None
    materials: list[Material] = []
    if session_factory:
        try:
            async with session_factory() as session:
                subject = await get_subject_by_id(session, subject_id, uid)
                if subject:
                    materials = await get_materials_by_subject(session, subject_id, uid)
        except Exception:
            logger.exception("Ошибка при загрузке предмета после удаления")

    if not subject:
        return

    total_pages = max(1, math.ceil(len(materials) / MATERIALS_PER_PAGE))
    learned_count = sum(1 for material in materials if material.learned_at is not None)
    text = get_subject_detail_text(subject.name, materials, learned_count, 1, total_pages)
    keyboard = get_subject_detail_keyboard(materials, subject_id, 1, total_pages)
    await update.effective_message.reply_text(text, reply_markup=keyboard, parse_mode="HTML")


async def on_delete_cancelled(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await on_back_to_file(update, context)


# ──────────────────────────────────────────────
# Удаление предмета
# ──────────────────────────────────────────────

async def on_delete_subject(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    uid = update.effective_user.id
    subject_id = context.user_data.get(UD_VIEWING_SUBJECT_ID)
    if not subject_id:
        await query.answer("Не удалось определить предмет.", show_alert=True)
        return

    session_factory = context.bot_data.get("session_factory")
    subject_name = "предмет"
    materials_count = 0
    if session_factory:
        try:
            async with session_factory() as session:
                subject = await get_subject_by_id(session, subject_id, uid)
                if subject:
                    subject_name = subject.name
                    materials_count = len(await get_materials_by_subject(session, subject_id, uid))
        except Exception:
            logger.exception("Ошибка при загрузке предмета для удаления")

    await query.message.reply_text(
        get_subject_delete_confirm_text(subject_name, materials_count),
        reply_markup=get_subject_delete_confirm_keyboard(),
        parse_mode="HTML",
    )


async def on_delete_subject_confirmed(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    uid = update.effective_user.id
    subject_id = context.user_data.get(UD_VIEWING_SUBJECT_ID)
    if not subject_id:
        await query.answer("Не удалось определить предмет.", show_alert=True)
        return

    session_factory = context.bot_data.get("session_factory")
    deleted = False
    subject_name = "предмет"
    if session_factory:
        try:
            async with session_factory() as session:
                subject = await get_subject_by_id(session, subject_id, uid)
                if subject:
                    subject_name = subject.name
                deleted = await delete_subject(session, subject_id, uid)
        except Exception:
            logger.exception("Ошибка при удалении предмета %s", subject_id)
            await query.edit_message_text("⚠️ Не удалось удалить предмет. Попробуй ещё раз.")
            return

    if not deleted:
        await query.edit_message_text("⚠️ Предмет не найден или уже удалён.")
        return

    context.user_data.pop(UD_VIEWING_SUBJECT_ID, None)
    context.user_data.pop(UD_VIEWING_SUBJECT_NAME, None)
    context.user_data.pop(UD_VIEWING_MATERIAL_ID, None)
    await query.edit_message_text(get_subject_deleted_text(subject_name), parse_mode="HTML")
    await send_subjects_screen(update, context)


async def on_delete_subject_cancelled(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await on_back_to_subject(update, context)


# ──────────────────────────────────────────────
# Регистрация
# ──────────────────────────────────────────────

def register(app: Application) -> None:
    # Просмотр предмета: sub:s:<id>
    app.add_handler(CallbackQueryHandler(on_subject_chosen, pattern=rf"^{CB_SUB_VIEW}\d+$"))
    # Пагинация: sub:pg:<id>:<page>
    app.add_handler(CallbackQueryHandler(on_page_changed, pattern=rf"^{CB_SUB_PAGE}\d+:\d+$"))
    # Просмотр файла: sub:f:<id>
    app.add_handler(CallbackQueryHandler(on_material_chosen, pattern=rf"^{CB_MAT_VIEW}\d+$"))
    # Удаление
    app.add_handler(CallbackQueryHandler(on_delete_subject, pattern=rf"^{CB_SUB_DEL}$"))
    app.add_handler(CallbackQueryHandler(on_delete_subject_confirmed, pattern=rf"^{CB_SUB_DEL_Y}$"))
    app.add_handler(CallbackQueryHandler(on_delete_subject_cancelled, pattern=rf"^{CB_SUB_DEL_N}$"))
    app.add_handler(CallbackQueryHandler(on_delete_material, pattern=rf"^{CB_MAT_DEL}$"))
    app.add_handler(CallbackQueryHandler(on_delete_confirmed, pattern=rf"^{CB_MAT_DEL_Y}$"))
    app.add_handler(CallbackQueryHandler(on_delete_cancelled, pattern=rf"^{CB_MAT_DEL_N}$"))
    # Назад
    app.add_handler(CallbackQueryHandler(on_back_to_subject, pattern=rf"^{CB_SUB_BACK}$"))
    app.add_handler(CallbackQueryHandler(on_back_to_file, pattern=rf"^{CB_FILE_BACK}$"))
    # Тесты (CB_SUB_TEST, CB_FILE_TEST) — в handlers/quiz.py
