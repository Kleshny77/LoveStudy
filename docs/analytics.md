# Аналитика и графики (минимум денег)

События пишутся в **ту же PostgreSQL**, что и бот. Графики — **Metabase** (скрипты в репозитории) или **Яндекс DataLens** вручную.

---

## Что уже сделано за тебя в коде

- Таблица **`analytics_events`**, фоновая запись из хендлеров (`services/analytics.py`).
- Скрипт **`scripts/setup_metabase.sh`** — на ВМ ставит Docker (если нет) и поднимает Metabase.
- Скрипт **`scripts/metabase_tunnel.sh`** — на Mac открывает безопасный туннель к Metabase.
- Скрипт **`scripts/check_analytics_events.py`** — проверяет, что таблица есть и сколько в ней строк.

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

- `main_menu_shown`, `open_screen`, `material_saved`, `deadline_created`, `pomodoro_work_completed`, `quiz_session_completed`, `subscription_paid`.

Отключить запись: `ANALYTICS_ENABLED=0` в `.env`.

---

## Примеры SQL в Metabase (New → Question → Raw SQL)

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
