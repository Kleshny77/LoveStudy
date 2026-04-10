# тексты и кнопки флоу загрузки

from telegram import InlineKeyboardMarkup

from constants import (
    CB_MAT_CANCEL,
    CB_MAT_CREATE,
    CB_MAT_FOLDER_PREFIX,
    CB_MAT_MORE,
    CB_MAT_TO_MAIN,
    CB_SUB_VIEW,
    MAX_FILE_SIZE_MB,
)
from services.ui import BUTTON_DANGER, BUTTON_PRIMARY, BUTTON_SUCCESS, em, ib


def get_instructions_text() -> str:
    return em(
        (
        "Пополняем базу знаний 📚\n\n"
        "Кидай сюда файлы для учебы:\n"
        "— PDF, DOCX, PPTX, TXT\n"
        "— Фото, видео, архивы и другие файлы\n\n"
        f"⚠️ Максимальный размер файла — {MAX_FILE_SIZE_MB} МБ.\n\n"
        "Я всё сохраню и смогу сделать из этого тест."
        )
    )


def get_instructions_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            ib("🔙 Назад", callback_data=CB_MAT_CANCEL),
            ib("🏠 Главное меню", callback_data=CB_MAT_TO_MAIN),
        ],
    ])


def get_file_too_big_text(size_mb: float) -> str:
    return (
        f"Файл слишком большой ({size_mb:.1f} МБ). "
        f"Максимум — {MAX_FILE_SIZE_MB} МБ.\n\n"
        "Попробуй сжать файл или загрузи по частям."
    )


def get_folder_choice_text(label: str) -> str:
    import html
    return em(f"«<b>{html.escape(label)}</b>» пойман! 🏆\n\nВ какую папку его положить?")


def get_folder_choice_keyboard(subjects: list[tuple[int, str]]) -> InlineKeyboardMarkup:
    buttons: list[list[object]] = []
    row: list[object] = []
    for sid, name in subjects:
        row.append(ib(name, callback_data=f"{CB_MAT_FOLDER_PREFIX}{sid}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([ib("+ Создать", callback_data=CB_MAT_CREATE, style=BUTTON_SUCCESS)])
    buttons.append([
        ib("🔙 Назад", callback_data=CB_MAT_CANCEL),
        ib("🏠 Главное меню", callback_data=CB_MAT_TO_MAIN),
    ])
    return InlineKeyboardMarkup(buttons)


def get_enter_folder_name_text() -> str:
    return "Как назовём папку или предмет?"


def get_enter_folder_name_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            ib("🔙 Назад", callback_data=CB_MAT_CANCEL),
            ib("🏠 Главное меню", callback_data=CB_MAT_TO_MAIN),
        ],
    ])


def get_done_text(folder_name: str, is_new_folder: bool) -> str:
    if is_new_folder:
        return em(f"✨ Готово!\n\nПапка «{folder_name}» создана, материал сохранён.")
    return em(f"✅ Готово! Материал сохранён в папку «{folder_name}».")


def get_done_keyboard(subject_id: int | None = None) -> InlineKeyboardMarkup:
    buttons = [[ib("📤 Загрузить ещё", callback_data=CB_MAT_MORE, style=BUTTON_PRIMARY, skip_custom_emoji=True)]]
    if subject_id is not None:
        buttons.append([
            ib(
                "📂 Посмотреть все файлы в папке",
                callback_data=f"{CB_SUB_VIEW}{subject_id}",
            )
        ])
    buttons.append([ib("🏠 В главное меню", callback_data=CB_MAT_TO_MAIN)])
    return InlineKeyboardMarkup(buttons)


def get_db_error_text() -> str:
    return em(
        (
        "⚠️ Не удалось сохранить в базу данных.\n"
        "Материал получен, но не сохранён. Попробуй ещё раз."
        )
    )


def get_no_db_text() -> str:
    return em("⚠️ База данных не настроена. Попроси администратора добавить DATABASE_URL на сервере.")
