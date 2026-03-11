# все callback_data и состояния (лимит Telegram: 64 байта на callback)

# ──────────────────────────────────────────────
# Главное меню
# ──────────────────────────────────────────────
CB_MAIN_MATERIALS = "main:materials"   # → промежуточный экран "Мои материалы"
CB_MAIN_UPLOAD    = "mat:upload"       # → флоу загрузки
CB_MAIN_SUBJECTS  = "main:subjects"   # → список предметов
CB_MAIN_DEADLINES = "main:deadlines"
CB_MAIN_PROFILE   = "main:profile"

# ──────────────────────────────────────────────
# Профиль и статистика
# ──────────────────────────────────────────────
CB_PROF_ACHIEV      = "prof:ach"
CB_PROF_STATS       = "prof:stats"
CB_PROF_SUBJECTS    = "prof:subs"
CB_PROF_SUBJECT     = "prof:sub:"     # prof:sub:<subject_id>
CB_PROF_DEADLINES   = "prof:ddl"
CB_PROF_MATERIALS   = "prof:mats"
CB_PROF_ACTIVITY    = "prof:act"
CB_PROF_PERIOD      = "prof:period"
CB_PROF_PERIOD_SET  = "prof:ps:"      # prof:ps:<week|month|semester|all>"
CB_ACH_HUB          = "ach:hub"
CB_ACH_BACK         = "ach:back"
CB_ACH_DISCIPLINE   = "ach:discipline"
CB_ACH_DEADLINES    = "ach:deadlines"
CB_ACH_MATERIALS    = "ach:materials"
CB_ACH_SERIES       = "ach:series"

# ──────────────────────────────────────────────
# Дедлайны
# ──────────────────────────────────────────────
CB_DDL_SUBJECTS      = "ddl:subjects"
CB_DDL_SUBJECT       = "ddl:subject:"     # ddl:subject:<subject_id>
CB_DDL_NEW_SUBJECT   = "ddl:new-subject"
CB_DDL_SETTINGS      = "ddl:settings"
CB_DDL_SETTINGS_SAVE = "ddl:settings:save"
CB_DDL_TOGGLE_MAIN   = "ddl:settings:main"
CB_DDL_TOGGLE_DAILY  = "ddl:settings:daily"
CB_DDL_SET_ON        = "ddl:set:on"
CB_DDL_SET_OFF       = "ddl:set:off"
CB_DDL_CREATE        = "ddl:create"
CB_DDL_REVIEW_CREATE = "ddl:review:create"
CB_DDL_REVIEW_EDIT   = "ddl:review:edit"
CB_DDL_EDIT_SUBJECT  = "ddl:edit:subject"
CB_DDL_EDIT_TITLE    = "ddl:edit:title"
CB_DDL_EDIT_DATE     = "ddl:edit:date"
CB_DDL_EDIT_TIME     = "ddl:edit:time"
CB_DDL_EDIT_DONE     = "ddl:edit:done"
CB_DDL_STEP_SUBJECT  = "ddl:step:subject"
CB_DDL_STEP_TITLE    = "ddl:step:title"
CB_DDL_STEP_DATE     = "ddl:step:date"
CB_DDL_STEP_TIME     = "ddl:step:time"
CB_DDL_ACTION_DONE   = "ddl:action:done"
CB_DDL_ACTION_MOVE   = "ddl:action:move"
CB_DDL_ACTION_DELETE = "ddl:action:delete"
CB_DDL_ACTION_REMIND = "ddl:action:remind"
CB_DDL_ACTION_PICK   = "ddl:pick:"        # ddl:pick:<action_code>:<deadline_id>
CB_DDL_REMIND_SET    = "ddl:remind:"      # ddl:remind:<minutes>
CB_DDL_REMIND_CUSTOM = "ddl:remind:custom"
CB_DDL_SUCCESS_SUBS  = "ddl:success:subs"
CB_DDL_BACK_HUB      = "ddl:back:hub"
CB_DDL_BACK_SUBJECTS = "ddl:back:subjects"
CB_DDL_BACK_SUBJECT  = "ddl:back:subject"

# Глобальная навигация (вне ConversationHandler)
CB_NAV_MAIN = "nav:main"   # → главное меню
CB_NAV_HUB  = "nav:hub"    # → экран «Мои предметы» (hub)
CB_NAV_SUBS = "nav:subs"   # → список предметов

# ──────────────────────────────────────────────
# Флоу загрузки (ConversationHandler)
# ──────────────────────────────────────────────
CB_MAT_FOLDER_PREFIX = "mat:f:"    # mat:f:<subject_id>
CB_MAT_CREATE        = "mat:create"
CB_MAT_CANCEL        = "mat:cancel"
CB_MAT_MORE          = "mat:more"
CB_MAT_TO_MAIN       = "mat:main"
CB_SUB_ADD           = "sub:add:"  # sub:add:<subject_id> — добавить файл в папку

# ──────────────────────────────────────────────
# Просмотр предметов и материалов
# ──────────────────────────────────────────────
CB_SUB_VIEW   = "sub:s:"    # sub:s:<subject_id>
CB_MAT_VIEW   = "sub:f:"    # sub:f:<material_id>
CB_SUB_PAGE   = "sub:pg:"   # sub:pg:<subject_id>:<page>
CB_SUB_DEL    = "sub:sdel"  # удалить текущий предмет
CB_SUB_DEL_Y  = "sub:sdly"  # подтвердить удаление предмета
CB_SUB_DEL_N  = "sub:sdln"  # отменить удаление предмета
CB_MAT_DEL    = "sub:del"   # удалить текущий материал (id из user_data)
CB_MAT_DEL_Y  = "sub:dly"   # подтвердить удаление
CB_MAT_DEL_N  = "sub:dln"   # отменить удаление
CB_SUB_BACK   = "sub:bk"    # назад к текущему предмету (id из user_data)
CB_FILE_BACK  = "sub:fb"    # назад к текущему файлу (id из user_data)
CB_SUB_TEST   = "sub:tst"   # тест по всем файлам (placeholder)
CB_FILE_TEST  = "sub:fts"   # тест по файлу (placeholder)
CB_SUB_TEST_MORE  = "sub:tst:more:"   # sub:tst:more:<subject_id>
CB_FILE_TEST_MORE = "sub:fts:more:"   # sub:fts:more:<material_id>

# ──────────────────────────────────────────────
# Состояния ConversationHandler загрузки
# ──────────────────────────────────────────────
ST_INSTRUCTIONS  = 1
ST_CHOOSE_FOLDER = 2
ST_ENTER_FOLDER  = 3

# ──────────────────────────────────────────────
# Ключи context.user_data
# ──────────────────────────────────────────────

# Загрузка файла
UD_IS_LINK       = "is_link"
UD_FILE_ID       = "f_id"
UD_FILE_UNIQUE   = "f_uid"
UD_FILE_NAME     = "f_name"
UD_FILE_SIZE     = "f_size"
UD_MIME_TYPE     = "f_mime"
UD_URL           = "f_url"

# Целевой предмет при "Добавить файл" из просмотра
UD_TARGET_SUBJECT_ID   = "tgt_sid"
UD_TARGET_SUBJECT_NAME = "tgt_snm"

# Текущий просматриваемый предмет / материал
UD_VIEWING_SUBJECT_ID   = "vs_id"
UD_VIEWING_SUBJECT_NAME = "vs_nm"
UD_VIEWING_MATERIAL_ID  = "vm_id"
UD_PROFILE_PERIOD       = "profile_period"
UD_ACH_BACK_CB         = "ach_back_cb"
UD_DDL_SUBJECT_ID       = "ddl_subject_id"
UD_DDL_SUBJECT_NAME     = "ddl_subject_name"
UD_DDL_TITLE            = "ddl_title"
UD_DDL_DATE             = "ddl_date"
UD_DDL_TIME             = "ddl_time"
UD_DDL_EDITING          = "ddl_editing"
UD_DDL_ACTION           = "ddl_action"
UD_DDL_SETTINGS_KIND    = "ddl_settings_kind"

# ──────────────────────────────────────────────
# Друзья и рейтинг
# ──────────────────────────────────────────────
CB_FRIENDS       = "main:friends"    # открыть хаб друзей
CB_FRI_RATING    = "fri:rating"      # посмотреть рейтинг
CB_FRI_LIST      = "fri:list"        # мои друзья
CB_FRI_INVITE    = "fri:invite"      # экран «Пригласить друга»
CB_FRI_LINK      = "fri:link"        # получить ссылку-приглашение
CB_FRI_ACHIEV    = "fri:achiev"      # мои достижения (placeholder)
CB_FRI_PROFILE   = "fri:profile"     # открыть свой профиль
CB_FRI_FPROF     = "fri:fprof"       # открыть профиль друга (вход в conv)

# Состояние ConversationHandler для поиска друга по @username
ST_FRI_SEARCH = 40

# Состояния ConversationHandler для дедлайнов
ST_DDL_SUBJECT_NAME  = 50
ST_DDL_TITLE         = 51
ST_DDL_DATE          = 52
ST_DDL_TIME          = 53
ST_DDL_ACTION_INDEX  = 54
ST_DDL_MOVE_DATE     = 55
ST_DDL_MOVE_TIME     = 56
ST_DDL_SETTINGS_TIME = 57
ST_DDL_REVIEW        = 58
ST_DDL_EDIT_MENU     = 59
ST_DDL_SETTINGS_MENU = 60
ST_DDL_SETTINGS_KIND = 61
ST_DDL_REMINDER_PICK = 62
ST_DDL_REMINDER_CUSTOM = 63

# ──────────────────────────────────────────────
# Pomodoro
# ──────────────────────────────────────────────
CB_POMO_OPEN    = "main:pomodoro"   # открыть экран помодоро
CB_POMO_START   = "pom:start"       # начать фокус
CB_POMO_PAUSE   = "pom:pause"
CB_POMO_RESUME  = "pom:resume"
CB_POMO_STOP    = "pom:stop"        # досрочно завершить
CB_POMO_SKIP    = "pom:skip"        # пропустить перерыв
CB_POMO_NEXT    = "pom:next"        # следующий цикл
CB_POMO_CFG     = "pom:cfg"         # настроить интервалы
CB_POMO_NOTIF   = "pom:notif"       # настройки уведомлений
CB_POMO_PRESET  = "pom:pre:"        # pom:pre:<work>:<break>
CB_POMO_CUSTOM  = "pom:cust"        # ручная настройка (вход в ConversationHandler)
CB_POMO_SOUND   = "pom:snd"         # настроить звук
CB_POMO_REMIND  = "pom:rem"         # настроить напоминание
CB_POMO_AUTO    = "pom:auto"        # настроить автозапуск перерыва
CB_POMO_SND_ON  = "pom:son"
CB_POMO_SND_OFF = "pom:sof"
CB_POMO_REM_ON  = "pom:ron"
CB_POMO_REM_OFF = "pom:rof"
CB_POMO_AUT_ON  = "pom:aon"
CB_POMO_AUT_OFF = "pom:aof"

# Состояние ConversationHandler для ввода ручного интервала
ST_POMO_CUSTOM = 20

# ──────────────────────────────────────────────
# Ограничения
# ──────────────────────────────────────────────
MAX_FILE_SIZE_MB   = 20
MATERIALS_PER_PAGE = 5
