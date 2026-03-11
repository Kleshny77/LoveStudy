# Декомпозиция экранов и флоу

Краткая карта: какой экран за что отвечает и где лежит код. Удобно править вручную.

---

## 1. Главный экран (Main)

**Когда:** команда `/start`.

**Что на экране:**
- Текст приветствия + «Здесь ты можешь» (5 пунктов) + «Выбери раздел ниже и начнём 👋».
- Кнопки (по макету): Загрузить материалы 📄 | Мои предметы 💖 | Дедлайны 🗓️ | Профиль 👤.

**Где править:**
- Текст: `services/main_menu.py` → `get_main_menu_text()`.
- Кнопки: `services/main_menu.py` → `get_main_menu_keyboard()`.
- Обработка: `handlers/main_menu.py` → `main_menu_callback()`.
- Показ по `/start`: `handlers/start.py` → `start()`.

**Callback_data:** `constants.py` — `CB_MAIN_UPLOAD` (mat:upload), `CB_MAIN_SUBJECTS`, `CB_MAIN_DEADLINES`, `CB_MAIN_PROFILE`.

---

## 2. Экран «Мои предметы»

**Когда:** нажатие «Мои предметы» на главном экране.

**Что на экране:**
- Текст про предметы и материалы.
- Кнопки: «Загрузить материалы» | «В главное меню».

**Где править:**
- Текст: `services/subjects_screen.py` → `get_subjects_screen_text()`.
- Кнопки: `services/subjects_screen.py` → `get_subjects_screen_keyboard()`.
- Показ экрана: `handlers/subjects.py` → `send_subjects_screen()` (вызывается из `main_menu.py` при `CB_MAIN_SUBJECTS`).
- Возврат в главное меню по «В главное меню»: `handlers/main_menu.py` → `back_to_main()` (callback `CB_MAT_BACK`).

**Callback_data:** `constants.py` — `CB_MAT_UPLOAD`, `CB_MAT_BACK`.

---

## 3. Флоу загрузки материалов (по макетам)

Вход: «Загрузить материалы» (главное меню или экран «Мои предметы»).  
Состояния: `STATE_INSTRUCTIONS` → `STATE_CHOOSE_FOLDER` → (опционально) `STATE_ENTER_FOLDER_NAME`.  
Данные: `context.user_data` — `UD_FILE_ID`, `UD_FILE_NAME`.

### 3.1 Инструкция

- Текст: «Пополняем базу знаний 📚» + «Кидай сюда всё, что есть:» + список форматов + «Я всё сохраню и смогу сделать из этого тест.»
- Кнопка: Назад (→ главное меню).

**Где:** `services/material_upload.py` — `get_instructions_text()`, `get_instructions_keyboard()`.  
Обработчики: `on_file_received()`, `on_back_from_instructions()`.

### 3.2 Выбор папки (после отправки файла)

- Текст: «Файл «…» пойман! 🏆 В какую папку его положить?»
- Кнопки: список папок (предметов из БД) по 2 в ряд, затем «+ Создать», затем «Отмена».

**Где:** `get_folder_choice_text()`, `get_folder_choice_keyboard(subjects)`.  
Обработчики: `on_folder_chosen()` (существующая папка), `on_create_folder()` (+ Создать), `on_cancel_folder_choice()` (Отмена → снова инструкция).

### 3.3 Имя новой папки (если нажали «+ Создать»)

- Текст: «Как назовем папку или предмет?»
- Кнопка: Назад (→ снова выбор папки).

**Где:** `get_enter_folder_name_text()`, `get_enter_folder_name_keyboard()`.  
Обработчики: `on_folder_name_entered()`, `on_back_from_folder_name()`.

### 3.4 Готово

- Текст: «✨ Готово! Папка «…» создана, файл сохранен.» или «Готово! Файл сохранен в папку «…»»
- Кнопки: Загрузить еще файл | В главное меню.

**Где:** `get_done_created_text()`, `get_done_saved_text()`, `get_done_keyboard()`.  
Обработчики: `on_upload_more()` (→ снова инструкция), `on_to_main()` (главное меню).  
Регистрация: `handlers/material_upload.py` → `register()` (ConversationHandler + callback для «Загрузить еще файл» и «В главное меню»).

---

## 4. База данных

- **Модели:** `db/models.py` — `User`, `Subject`, `Material`.
- **Сохранение:** `db/repositories.py` — `get_or_create_user()`, `get_or_create_subject()`, `create_material()`. Вызов из `handlers/material_upload.py` → `on_confirm_yes()` при нажатии «Да, верно».

При отсутствии `DATABASE_URL` в `.env` бот работает без БД; при нажатии «Да, верно» будет сообщение «БД не настроена».
