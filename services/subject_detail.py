# тексты и клавиатуры для экранов: список предметов, детали предмета, детали файла

from telegram import InlineKeyboardMarkup

from constants import (
    CB_FILE_BACK,
    CB_FILE_TEST,
    CB_MAT_CANCEL,
    CB_MAT_DEL,
    CB_MAT_DEL_N,
    CB_MAT_DEL_Y,
    CB_MAT_TO_MAIN,
    CB_MAT_VIEW,
    CB_MAIN_UPLOAD,
    CB_NAV_HUB,
    CB_NAV_MAIN,
    CB_NAV_SUBS,
    CB_SUB_ADD,
    CB_SUB_BACK,
    CB_SUB_DEL,
    CB_SUB_DEL_N,
    CB_SUB_DEL_Y,
    CB_SUB_PAGE,
    CB_SUB_TEST,
    CB_SUB_VIEW,
    MATERIALS_PER_PAGE,
)
from db.models import Material
from services.ui import BUTTON_DANGER, BUTTON_PRIMARY, BUTTON_SUCCESS, em, ib

_TYPE_EMOJI: dict[str, str] = {
    "PDF":        "📄",
    "Архив":      "📦",
    "Изображение":"🖼️",
    "Видео":      "🎬",
    "Аудио":      "🎵",
    "Документ":   "📝",
    "Ссылка":     "🔗",
    "Файл":       "📄",
}


def _emoji(material_type: str) -> str:
    return _TYPE_EMOJI.get(material_type, "📄")


def _short(text: str, limit: int = 28) -> str:
    return text[:limit] + "…" if len(text) > limit else text


# ──────────────────────────────────────────────
# Список предметов
# ──────────────────────────────────────────────

def get_subjects_list_text(count: int) -> str:
    if count == 0:
        return em(
            (
            "📂 <b>Твоя цифровая полка</b>\n\n"
            "Пока здесь пусто.\nЗагрузи первый файл — предмет появится автоматически!"
            )
        )
    return em(
        (
        "📂 <b>Твоя цифровая полка</b>\n\n"
        "Выбери предмет — внутри лежат все загруженные материалы."
        )
    )


def get_subjects_list_keyboard(subjects: list[tuple[int, str]]) -> InlineKeyboardMarkup:
    buttons: list[list[object]] = []
    row: list[object] = []
    for sid, name in subjects:
        row.append(ib(name, callback_data=f"{CB_SUB_VIEW}{sid}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    if not subjects:
        buttons.append([ib("📤 Загрузить первый файл", callback_data=CB_MAIN_UPLOAD, style=BUTTON_PRIMARY, skip_custom_emoji=True)])
    buttons.append([
        ib("🔙 Назад", callback_data=CB_NAV_HUB),
        ib("🏠 Главное меню", callback_data=CB_NAV_MAIN),
    ])
    return InlineKeyboardMarkup(buttons)


# ──────────────────────────────────────────────
# Детали предмета
# ──────────────────────────────────────────────

def get_subject_detail_text(
    subject_name: str,
    materials: list[Material],
    learned_count: int,
    page: int,
    total_pages: int,
) -> str:
    total = len(materials)
    if total == 0:
        return em(
            (
            f"📐 <b>Предмет: {subject_name}</b>\n\n"
            "Пока нет файлов. Загрузи первый!"
            )
        )

    lines = [f"📐 <b>Предмет: {subject_name}</b>\n"]
    lines.append(f"Файлы в базе ({total}):")
    for m in materials:
        emoji = _emoji(m.material_type)
        name = m.original_filename or m.url or "файл"
        lines.append(f"{emoji} {_short(name, 40)}")

    learned_count = max(0, min(learned_count, total))
    lines.append(f"\n<i>Твой прогресс: 🧠 Выучено тем: {learned_count}/{total}</i>")
    if total_pages > 1:
        lines.append(f"\n<i>Страница {page} из {total_pages}</i>")
    return em("\n".join(lines))


def get_subject_detail_keyboard(
    materials: list[Material],
    subject_id: int,
    page: int,
    total_pages: int,
) -> InlineKeyboardMarkup:
    # Файлы текущей страницы
    start = (page - 1) * MATERIALS_PER_PAGE
    page_materials = materials[start : start + MATERIALS_PER_PAGE]

    buttons: list[list[object]] = []

    for m in page_materials:
        emoji = _emoji(m.material_type)
        label = m.original_filename or m.url or "файл"
        buttons.append([
            ib(
                f"{emoji} {_short(label, 30)}",
                callback_data=f"{CB_MAT_VIEW}{m.id}",
            )
        ])

    # Пагинация
    nav_row: list[object] = []
    if page > 1:
        nav_row.append(ib(
            f"◀ Стр {page - 1}",
            callback_data=f"{CB_SUB_PAGE}{subject_id}:{page - 1}",
        ))
    if page < total_pages:
        nav_row.append(ib(
            f"Стр {page + 1} ▶",
            callback_data=f"{CB_SUB_PAGE}{subject_id}:{page + 1}",
        ))
    if nav_row:
        buttons.append(nav_row)

    # Действия
    buttons.append([ib("✨ Тест по ВСЕМ файлам", callback_data=CB_SUB_TEST, style=BUTTON_PRIMARY)])
    buttons.append([ib("📥 Добавить файл", callback_data=f"{CB_SUB_ADD}{subject_id}", style=BUTTON_SUCCESS, skip_custom_emoji=True)])
    buttons.append([ib("🗑️ Удалить предмет", callback_data=CB_SUB_DEL, style=BUTTON_DANGER)])
    buttons.append([
        ib("🔙 Назад", callback_data=CB_NAV_SUBS),
        ib("🏠 Главное меню", callback_data=CB_NAV_MAIN),
    ])
    return InlineKeyboardMarkup(buttons)


# ──────────────────────────────────────────────
# Детали файла (кнопки — отправляется вместе с файлом/ссылкой)
# ──────────────────────────────────────────────

def get_file_detail_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [ib("🧠 Сгенерировать тест по файлу", callback_data=CB_FILE_TEST, style=BUTTON_PRIMARY)],
        [ib("🗑️ Удалить", callback_data=CB_MAT_DEL, style=BUTTON_DANGER)],
        [
            ib("🔙 Назад", callback_data=CB_SUB_BACK),
            ib("🏠 Главное меню", callback_data=CB_NAV_MAIN),
        ],
    ])


def get_file_link_text(url: str, description: str | None) -> str:
    label = description or url
    return em(f"🔗 <b>Ссылка:</b> <a href=\"{url}\">{_short(label, 60)}</a>")


# ──────────────────────────────────────────────
# Подтверждение удаления
# ──────────────────────────────────────────────

def get_delete_confirm_text(material_name: str) -> str:
    return em(
        (
        f"⚠️ Ты уверен, что хочешь удалить <b>«{material_name}»</b>?\n\n"
        "Это действие нельзя отменить."
        )
    )


def get_delete_confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            ib("✅ Да, удалить", callback_data=CB_MAT_DEL_Y, style=BUTTON_DANGER),
            ib("❌ Оставить", callback_data=CB_MAT_DEL_N, style=BUTTON_SUCCESS),
        ],
        [
            ib("🔙 Назад", callback_data=CB_FILE_BACK),
            ib("🏠 Главное меню", callback_data=CB_NAV_MAIN),
        ],
    ])


def get_deleted_text(material_name: str) -> str:
    return em(f"🗑️ Файл <b>«{_short(material_name, 40)}»</b> удалён.")


def get_subject_delete_confirm_text(subject_name: str, materials_count: int) -> str:
    suffix = (
        f"и все {materials_count} файлов внутри"
        if materials_count > 0
        else "даже если файлов внутри пока нет"
    )
    return em(
        f"⚠️ Ты уверен, что хочешь удалить предмет <b>«{subject_name}»</b> {suffix}?\n\n"
        "Это действие нельзя отменить."
    )


def get_subject_delete_confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            ib("✅ Да, удалить", callback_data=CB_SUB_DEL_Y, style=BUTTON_DANGER),
            ib("❌ Оставить", callback_data=CB_SUB_DEL_N, style=BUTTON_SUCCESS),
        ],
        [
            ib("🔙 Назад", callback_data=CB_SUB_BACK),
            ib("🏠 Главное меню", callback_data=CB_NAV_MAIN),
        ],
    ])


def get_subject_deleted_text(subject_name: str) -> str:
    return em(f"🗑️ Предмет <b>«{_short(subject_name, 40)}»</b> удалён.")


# ──────────────────────────────────────────────
# Добавить файл в конкретный предмет
# ──────────────────────────────────────────────

def get_add_to_subject_text(subject_name: str) -> str:
    return em(
        (
        f"📥 <b>Пополняем папку «{subject_name}»</b>\n\n"
        "Кидай сюда учебные файлы:\n"
        "— PDF, DOCX, PPTX, TXT\n"
        "— Фото, видео, архивы и другие файлы\n\n"
        f"⚠️ Максимальный размер файла — 20 МБ."
        )
    )


def get_add_to_subject_keyboard() -> InlineKeyboardMarkup:
    """Кнопки Назад/Главное меню — CB_MAT_* чтобы fallbacks ConversationHandler сбрасывали состояние."""
    return InlineKeyboardMarkup([
        [
            ib("🔙 Назад", callback_data=CB_MAT_CANCEL),
            ib("🏠 Главное меню", callback_data=CB_MAT_TO_MAIN),
        ],
    ])


def get_add_done_text(filename: str, subject_name: str) -> str:
    return em(f"✅ Файл <b>«{_short(filename, 35)}»</b> сохранён в папку <b>«{subject_name}»</b>.")


def get_add_done_keyboard(subject_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [ib("📥 Добавить ещё файл", callback_data=f"{CB_SUB_ADD}{subject_id}", style=BUTTON_SUCCESS, skip_custom_emoji=True)],
        [ib("📂 Посмотреть все файлы в папке", callback_data=f"{CB_SUB_VIEW}{subject_id}", style=BUTTON_PRIMARY)],
        [ib("🏠 В главное меню", callback_data=CB_NAV_MAIN)],
    ])
