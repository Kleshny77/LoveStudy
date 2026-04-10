# Аналитика и графики (минимум денег)

События пишутся в **ту же PostgreSQL**, что и бот. Графики — **Metabase** (скрипты в репозитории) или **Яндекс DataLens** вручную.

---

## Что уже сделано за тебя в коде

- Таблица **`analytics_events`**, фоновая запись из хендлеров (`services/analytics.py`).
- Скрипт **`scripts/setup_metabase.sh`** — на ВМ ставит Docker (если нет) и поднимает Metabase.
- Скрипт **`scripts/metabase_tunnel.sh`** — на Mac открывает безопасный туннель к Metabase.
- Скрипт **`scripts/check_analytics_events.py`** — проверяет, что таблица есть и сколько в ней строк.
- Скрипт **`scripts/print_analytics_report.py`** — **DAU за 14 дней**, счётчики событий, каналы, помодоро и т.д. **в терминале** одной командой (тот же `DATABASE_URL`, что у бота). Metabase для этого не обязателен.

### Сводка метрик в терминале (без ручного SQL в Metabase)

На Mac или на ВМ после `cd ~/app`:

```bash
./venv/bin/python scripts/print_analytics_report.py
```

Нужен рабочий `.env` с `DATABASE_URL`. Это не заменяет графики в Metabase, но даёт те же цифры без кликов в UI.

---

## Что без тебя никак (я не могу залогиниться в твой браузер / облако)

1. **Пароль sudo** на ВМ при первом запуске `setup_metabase.sh` (если ставится Docker).
2. **Первый вход в Metabase** в браузере: имя админа, пароль — только ты.
3. **Add database в Metabase**: хост, логин, пароль PostgreSQL — из твоего `~/app/.env` (я не вижу твой `.env`).
4. Опционально **DataLens** — авторизация в Яндексе и создание подключения в их UI.

Всё остальное ниже — по шагам «скопировал команду → Enter».

---

## Где какая папка (чтобы не путаться)

| Машина | Путь к коду LoveStudy | Что делать |
|--------|------------------------|------------|
| **Mac** | `/Users/kleshny/ВШЭ/LoveStudy` | `rsync`, `bash scripts/metabase_tunnel.sh` |
| **ВМ (сервер)** | `/home/kleshny/app` (= `~/app` **на сервере**) | `bash ~/app/scripts/setup_metabase.sh`, бот, systemd |

На Mac **`bash ~/app/scripts/...` НЕ РАБОТАЕТ** — у тебя на Mac `~/app` это не репозиторий. Скрипты из `scripts/` для сервера запускай **после** `ssh`, на ВМ.

---

## Полный порядок команд (деплой + бот + Metabase + проверка)

### 1) Только на Mac — выгрузить код и перезапустить бота на сервере

Один блок, целиком вставь в терминал **на Mac**:

```bash
cd "/Users/kleshny/ВШЭ"
rsync -avz \
  --exclude venv --exclude .venv --exclude .env --exclude .git --exclude .DS_Store \
  ./LoveStudy/ kleshny@158.160.143.175:~/app/
ssh kleshny@158.160.143.175 "cd ~/app && source venv/bin/activate && pip install -q -r requirements.txt && sudo systemctl restart lovestudy && sudo systemctl status lovestudy --no-pager"
```

- `.env` на сервере **не трогается** (он в exclude) — токен и `DATABASE_URL` как настроил, так и останутся.
- Если логин/IP другие — замени `kleshny@158.160.143.175` везде ниже тоже.

### 2) Только на ВМ — Metabase (Docker + контейнер)

Сначала зайди на сервер:

```bash
ssh kleshny@158.160.143.175
```

Уже **внутри SSH** (приглашение типа `kleshny@compute-vm-...`):

```bash
bash ~/app/scripts/setup_metabase.sh
```

Дождись окончания. Выйти из SSH: `exit`

### 3) Только на Mac — туннель к Metabase

**Новое** окно терминала на Mac:

```bash
cd "/Users/kleshny/ВШЭ/LoveStudy"
bash scripts/metabase_tunnel.sh
```

Оставь окно открытым. В браузере: **http://localhost:3000** → регистрация админа → **Add database** → данные PostgreSQL из `DATABASE_URL` в файле на сервере `~/app/.env` (хост, порт `6432`, БД, пользователь, пароль; SSL — по требованию Yandex).

### 4) Только на ВМ — проверить, что события пишутся в БД

```bash
ssh kleshny@158.160.143.175
cd ~/app && ./venv/bin/python scripts/check_analytics_events.py
exit
```

---

## Таблица `analytics_events`

| Колонка | Описание |
|---------|----------|
| `id` | BIGSERIAL |
| `user_telegram_id` | Telegram user id |
| `event_name` | см. `services/analytics.py` |
| `properties` | JSONB |
| `created_at` | UTC |

### Имена событий

| Событие | Свойства (JSON) |
|---------|-----------------|
| `bot_started` | Каждый `/start`: `is_new_user`, `from_invite`, `acquisition_ref`, `start_token` |
| `main_menu_shown` | `from_invite`, `acquisition_ref` |
| `open_screen` | `screen` |
| `material_saved` | `new_subject`, `subject_id` |
| `deadline_created` | `has_subject_id` |
| `pomodoro_work_completed` | `work_minutes` |
| `quiz_generated` | `kind` (`subject` \| `file`), `subject_id`, `material_id`, `question_count` |
| `quiz_session_completed` | `passed`, `correct_answers`, `wrong_answers`, `total_questions` |
| `subscription_paid` | `total_amount`, `currency` |

**Deep link:** `https://t.me/<bot>?start=ref_<канал>` — токен после `ref_`: латиница, цифры, `_`, `-`, до 64 символов. В `users.acquisition_ref` сохраняется **первый** непустой канал (`invite` для `invite_<id>` или значение после `ref_`).

Отключить запись: `ANALYTICS_ENABLED=0` в `.env`.

---

## Карта метрик LoveStudy (лекция 5 УП + продуктовая воронка)

Ниже — **релевантный** набор: что уже можно считать в Metabase/DataLens по текущей БД, что покрывается только частично, и что логично добавить в код (события/поля). Идеи **Day 1/7/30 retention**, **engagement**, **TTFKA**, **частота**, **первая сессия**, **NPS**, **churn**, **сегменты** — из лекции 5 (блок «Что отслеживать»); кейсы про конфликты метрик (Facebook, Spotify и т.д.) в той же лекции напоминают: перед оптимизацией одной цифры проверяй, не ломаешь ли удержание или монетизацию.

### Источники данных в проекте

| Источник | Зачем |
|----------|--------|
| `users` | Регистрации (`created_at`), подписка (`subscription_expires_at`), активность (`last_activity_date`), **`acquisition_ref`** (первый канал из `/start`), агрегаты по квизам (`quiz_correct_answers`, `quiz_wrong_answers`), дневной лимит генераций (`quiz_generations_today` / `quiz_generations_date` — **без истории по дням**) |
| `analytics_events` | Продуктовые события и разрезы (`event_name`, `properties`, `created_at`) — см. `services/analytics.py` |
| `materials`, `subjects`, `deadlines` | Факты создания контента и планирования (даты, пользователь) |
| `pomodoro_session_logs` | Завершённые рабочие фазы помодоро (`work_minutes`, `completed_at`) |
| `friendships` | Социальные связи (по времени `created_at`) |

---

### Ключевые метрики (как в ТЗ продукта)

| Метрика | Смысл | LoveStudy сейчас | Как считать / комментарий |
|--------|--------|------------------|---------------------------|
| **Total users** | Всего зарегистрированных | Да | `count(*)` из `users` |
| **DAU** | Уникальные пользователи с активностью за день | Частично | По **`analytics_events`** (любое событие) или по **`last_activity_date = сегодня`** (если бот обновляет поле при действиях — проверь актуальность). WAU/MAU — то же с `date_trunc('week'/'month', ...)` |
| **Retention (D1/D7/D30)** | Вернулись ли на 1-й / 7-й / 30-й день после регистрации | Частично | Когорта: `users.created_at` → наличие события или `last_activity_date` в окне **день N** (календарный день относительно `created_at`). Точнее — по дням активности из событий |
| **Среднее число сгенерированных тестов** | Сколько раз пользователь запускал генерацию | Да (история) | События **`quiz_generated`** в `analytics_events`; дневной лимит по-прежнему в `users` |
| **Частота Pomodoro** | Насколько часто закрывают рабочие сессии | Да | `pomodoro_session_logs`: число сессий и `sum(work_minutes)` на пользователя/неделю; дублируется смыслом с `pomodoro_work_completed` в аналитике |
| **Доля Premium** | % пользователей с активной подпиской | Да | Доля `users` с `subscription_expires_at > now()` от total (или от активных за период — зафиксируй знаменатель в определении) |
| **ARPU** | Доход на пользователя за период | Частично | Сумма `subscription_paid.total_amount` из событий / на paying users или на MAU — **после согласования**: валюта Stars, период, gross vs net |

---

### Метрики из лекции («Что отслеживать») — применение к боту

| Тема лекции | Что измеряет | LoveStudy |
|-------------|--------------|-----------|
| **Engagement** | Частота и глубина использования ключевых функций | Плюс `bot_started`, `quiz_generated`; события `open_screen`, `material_saved`, `deadline_created`, `pomodoro_work_completed`, `quiz_session_completed`; плюс сырые строки в `materials` / `deadlines` / `pomodoro_session_logs` |
| **Time to first key action (TTFKA)** | Время от регистрации до первого «целевого» действия | **Нет готового поля.** Считается в SQL: `min(event.created_at) - users.created_at` для выбранного события (например первый `material_saved` или `deadline_created`). Нужна полнота событий по всем целевым действиям |
| **Frequency of use** | Ежедневно / еженедельно / ежемесячно возвращаются | DAU/WAU/MAU и распределение «дней с активностью» за 7/28 дней по `analytics_events` |
| **Onboarding completion** | Дошли ли до конца введения | В боте нет явного чеклиста онбординга в БД — только **прокси**: дошёл до `main_menu_shown`, сделал ли что-то за первые 24 ч |
| **First session activity** | Что сделали сразу после старта | В рамках **первого календарного дня** после `users.created_at`: какие `event_name` встречаются (и в каком порядке — сложнее, нужна сортировка по `created_at`) |
| **Retention by acquisition channel** | Удержание по источнику | `users.acquisition_ref`, свойства `bot_started` / `main_menu_shown`; ссылки вида `?start=ref_vk` |
| **NPS / early feedback** | Готовность рекомендовать | **Не в БД** — опрос в боте, форма, интервью; можно завести событие `nps_score` с `score`, `cohort_days` |
| **Churn rate** | Перестали пользоваться за период | Определи «активен»: был ивент или обновлён `last_activity_date` за последние N дней → доля «был в прошлом окне, нет в текущем» |
| **Behavioral segmentation** | Сегменты по поведению | В Metabase: представление/запрос — пользователь + метрики за 28 дней (сессии помодоро, материалы, тесты, дедлайны) → кластеры «фокус / только файлы / тесты» и т.д. |

---

### Воронка (как в описании продукта)

Этапы ниже — **логические**; в SQL это обычно воронка «у пользователя когда-то было событие A, потом B» или «в первые 7 дней после регистрации».

1. **Acquisition** — `bot_started`, `users.created_at`, **`acquisition_ref`**, `from_invite` / `start_token`.
2. **Activation** — первое ключевое действие: первый предмет (`subjects`), первая загрузка (`material_saved` / `materials`), первый дедлайн (`deadline_created`), **`quiz_generated`** (старт генерации) и `quiz_session_completed` (прохождение).
3. **Engagement** — повторные `open_screen`, регулярные `pomodoro_work_completed`, `quiz_session_completed`, новые `materials` / `deadlines`.
4. **Retention** — возвраты по DAU/WAU и когортам D1/D7/D30.
5. **Monetization (Premium)** — `subscription_paid`, состояние `subscription_expires_at`, конверсия free → paid.

---

### Уже в коде (расширение аналитики)

- **`quiz_generated`** — после успешной генерации и отправки опросов.
- **`bot_started`** — при каждом `/start` (отдельно от показа меню с задержкой).
- **`ref_<канал>`** и **`invite_<id>`** → `users.acquisition_ref` (`invite` или токен после `ref_`).

Опционально позже: **NPS** (событие с оценкой), длительность сессии в секундах.

---

## Примеры SQL в Metabase (New → Question → Raw SQL)

**Полный набор запросов (DAU/WAU/MAU, retention, воронка, Premium, тесты, помодоро и т.д.)** — один файл, блоки разделены комментариями:  
**[`sql/metabase_all_metrics.sql`](../sql/metabase_all_metrics.sql)**  
В Metabase создавай **отдельный вопрос на каждый блок** между линиями `====`.

DAU по событиям:

```sql
SELECT
  date_trunc('day', created_at) AS day,
  count(DISTINCT user_telegram_id) AS dau
FROM analytics_events
WHERE created_at >= now() - interval '30 days'
GROUP BY 1
ORDER BY 1;
```

Счётчики по типам:

```sql
SELECT event_name, count(*) AS n
FROM analytics_events
WHERE created_at >= now() - interval '30 days'
GROUP BY 1
ORDER BY n DESC;
```

---

## Вариант: Яндекс DataLens

Подключение к Managed PostgreSQL из [DataLens](https://datalens.yandex.ru) — вручную в интерфейсе; лучше отдельный read-only пользователь для БД. Данные те же (`analytics_events`).

---

## Metabase не коннектится к Yandex PostgreSQL

1. Убедись, что Metabase в Docker **на ВМ** (`sudo docker ps | grep metabase`), а в браузере `localhost` — это **SSH-туннель** на эту ВМ.
2. На ВМ выполни (проверка тем же `DATABASE_URL`, что у бота):

```bash
cd ~/app && bash scripts/test_pg_connection.sh
```

Если тут **ошибка** — чиним сеть/SG/пароль, Metabase тут ни при чём. Если **`ok`** — значит Metabase на этой же ВМ должен подключаться **к тем же** `Host`, `Port`, `Database name`, `Username`, `Password`, что в `DATABASE_URL` (частая ошибка — подставить `localhost`: это хост **кластера Yandex**, не ВМ и не `127.0.0.1`).

Если **`test_pg_connection.sh` = ok**, а Metabase по-прежнему «не коннектится», проверь **тот же network namespace, что у контейнера Metabase** (иногда с хоста psql проходит, а из Docker bridge — нет):

```bash
cd ~/app && bash scripts/test_pg_metabase_network.sh
```

Если **здесь ошибка**, а обычный psql на ВМ — **ok**: перезапусти Metabase свежим **`scripts/setup_metabase.sh`** с репозитория — скрипт поднимает Metabase в **`--network host`** (исходящий трафик как у `psql`), UI по-прежнему только на `127.0.0.1:3000`.

Логи `tail -100` **без** нажатия «Проверить соединение» в UI часто не содержат JDBC-ошибки. Сделай так: в одном SSH-сеансе запусти поток логов, в браузере нажми «Проверить соединение», вернись в SSH и останови `Ctrl+C`:

```bash
sudo docker logs -f metabase 2>&1
```

Либо сразу после неудачной проверки:

```bash
sudo docker logs metabase 2>&1 | grep -iE 'error|exception|jdbc|postgres|ssl|certificate' | tail -40
```

3. В Metabase попробуй по очереди: **SSL `require`** без загрузки CA; затем **`verify-ca`** с CA из [Yandex CA.pem](https://storage.yandexcloud.net/cloud-certs/CA.pem). Не используй **`verify-full`**, если не уверен в совпадении hostname. **Не смешивай:** если в UI стоит **`verify-ca`** и загружен PEM, в поле JDBC **не пиши** `sslmode=require` — оставь там только например `prepareThreshold=0` (иначе драйвер получает противоречивые настройки SSL).
4. Поле **Connection string** оставь **пустым**, только Host / Port / DB / User / Password. Порт **6432** в Yandex — часто **пулер** (не прямой Postgres). `psql` с ним может работать, а **JDBC (Metabase)** — нет из‑за prepared statements. В **Additional JDBC connection string options** добавь: `prepareThreshold=0` (отключает server-side prepare; часто это сразу чинит «не могу подключиться» на 6432). Альтернатива: открыть в SG порт **5432** к подсети ВМ и в Metabase указать **5432** на том же хосте.
5. В **Additional JDBC connection string options** при необходимости можно дублировать `sslmode=require` (если режим SSL в форме уже «require», обычно достаточно галочки SSL). При `verify-ca` обычно достаточно загруженного PEM в форме.

---

## Переменная `LOVESTUDY_SSH`

Как в `diagnose.sh`: для туннеля можно указать хост.

```bash
LOVESTUDY_SSH=user@ip bash scripts/metabase_tunnel.sh
```

---

## Metabase выключить / включить (когда не смотришь графики)

- **Сбор событий** делает **бот** → пишет в PostgreSQL. От Metabase это **не зависит**. Контейнер остановлен — события **всё равно копятся** (пока работает бот и есть `DATABASE_URL`).
- **Metabase** — только витрина: жрёт **RAM/CPU на той же ВМ**, отдельной подписки нет. Не смотришь неделю — можно остановить:

```bash
# на ВМ по SSH
sudo docker stop metabase
```

Снова смотреть графики:

```bash
sudo docker start metabase
# на Mac: bash scripts/metabase_tunnel.sh → http://localhost:3000
```

Полностью убрать контейнер (Metabase сбросит свои локальные настройки внутри контейнера, **данные в PostgreSQL не тронет**):

```bash
sudo docker rm -f metabase
# потом снова: bash ~/app/scripts/setup_metabase.sh
```
