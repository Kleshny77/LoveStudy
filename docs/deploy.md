# Деплой в Yandex Cloud

Инструкция: ВМ для бота + по желанию Managed PostgreSQL. Грант — [консоль Yandex Cloud](https://console.cloud.yandex.ru).

---

## Чеклист: новый аккаунт Yandex Cloud

1. **Облако и биллинг** — привязан платёжный аккаунт, активен грант/баланс.
2. **Сеть** — достаточно стандартной сети `default` (как в консоли «Облачные сети»).
3. **ВМ** — Ubuntu 22.04 или 24.04 LTS, публичный IP, SSH-ключ, та же **зона доступности**, что у кластера БД (сейчас ВМ в `ru-central1-d`).
4. **Группы безопасности** — входящий **22/tcp** (лучше с твоего IP, не `0.0.0.0/0`), исходящий трафик разрешён (для Telegram и БД).
5. **Managed PostgreSQL** — та же **облачная сеть** `default`, подсеть в той же зоне; в настройках доступа разрешить хосты из подсети ВМ (или SG ВМ → SG кластера на **6432/tcp**).
6. **На ВМ** — скачать `~/.postgresql/root.crt`, в `~/app/.env` указать `DATABASE_URL` с **одним** хостом (мастер) и портом **6432**, `sslmode=require`.

Подробнее по шагам 3–5 — в разделах ниже.

### Зафиксировано для текущего стенда (подсети / БД)

| Что | Значение |
|-----|----------|
| Облачная сеть | `default` |
| Зона ВМ и кластера БД | `ru-central1-d` |
| Подсеть ВМ | `default-ru-central1-d` |
| **CIDR для правил доступа к PostgreSQL** | **`10.131.0.0/24`** (вход с этой подсети на **TCP 6432**) |
| Публичный IP ВМ (шпаргалка SSH) | `158.160.143.175` |

Подсети в других зонах (`10.128.0.0/24` в `1a`, `10.129.0.0/24` в `1b`) для этой ВМ не использовать.

---

## Шпаргалка команд (kleshny @ 158.160.143.175)

Актуально для текущей ВМ. Если сменится **публичный IP** или **логин** — поправь команды ниже.

### Где выполнять команды

| Где | Что |
|-----|-----|
| **На Mac** | `cd`, `rsync`, `ssh user@host "команда"` — только выкладка кода и удалённый one-liner |
| **На ВМ (после `ssh …`)** | `sudo`, `systemctl`, `journalctl`, пути `/home/kleshny/...`, файлы в `/etc/systemd/system/` |

На macOS **нет** `systemctl`. Путь **`/home/kleshny/app`** существует **только на сервере**. Если видишь **`systemctl: command not found`** или **`cp: /home/kleshny/...: No such file or directory`** на Mac — открой сессию SSH и повтори команды там.

**Подключиться по SSH:**
```bash
ssh kleshny@158.160.143.175
```

**Залить код на сервер** (на маке, из **родительской** папки `LoveStudy`, например `ВШЭ`):
```bash
cd "/Users/kleshny/ВШЭ"
rsync -avz --exclude venv --exclude .venv --exclude .env --exclude .git --exclude .DS_Store ./LoveStudy/ kleshny@158.160.143.175:~/app/
```

**Пункт 3 — systemd (бот в фоне).** Только **на ВМ**, в сессии SSH (см. таблицу выше). Выполни по порядку.

Шаг 1 — создать файл юнита. Выполни:
```bash
sudo nano /etc/systemd/system/lovestudy.service
```

Шаг 2 — в nano вставь **только** эти строки (копируй блок ниже, без слова bash и без обрамления тройными кавычками):
```
[Unit]
Description=LoveStudy Telegram Bot
After=network.target

[Service]
Type=simple
User=kleshny
WorkingDirectory=/home/kleshny/app
ExecStart=/home/kleshny/app/venv/bin/python3 -m bot
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```
Сохрани: Ctrl+O, Enter, затем выход: Ctrl+X.

Шаг 3 — включить и запустить:
```bash
sudo systemctl daemon-reload
sudo systemctl enable lovestudy
sudo systemctl start lovestudy
sudo systemctl status lovestudy
```

Если видишь **`Unit lovestudy.service not found`** — юнит ещё не создан. Варианты (всё **на ВМ по SSH**):

1. Шаги 1–2 выше (`nano` + вставка блока `[Unit]…`).
2. После свежего `rsync` с мака (в репозитории есть `deploy/lovestudy.service`):
   ```bash
   sudo cp /home/kleshny/app/deploy/lovestudy.service /etc/systemd/system/lovestudy.service
   sudo systemctl daemon-reload
   sudo systemctl enable --now lovestudy
   sudo systemctl status lovestudy
   ```
3. Если **`deploy/lovestudy.service` на сервере нет** (старый `rsync` без папки `deploy/`) — на ВМ выполни (**важно:** строка `EOF` в конце — без пробелов в начале, иначе heredoc не сработает):

```bash
sudo tee /etc/systemd/system/lovestudy.service >/dev/null <<'EOF'
[Unit]
Description=LoveStudy Telegram Bot
After=network.target

[Service]
Type=simple
User=kleshny
WorkingDirectory=/home/kleshny/app
ExecStart=/home/kleshny/app/venv/bin/python3 -m bot
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
sudo systemctl daemon-reload
sudo systemctl enable --now lovestudy
sudo systemctl status lovestudy
```

Если логин на ВМ не `kleshny` или приложение не в `~/app` — перед запуском поправь `User=` и пути внутри блока выше (можно через `sudo nano /etc/systemd/system/lovestudy.service`).

Если статус `active (running)` — бот крутится в фоне. Логи смотреть так:
```bash
journalctl -u lovestudy -f
```
Если `journalctl` пишет, что не видишь сообщения других пользователей — используй `sudo journalctl -u lovestudy -f`. Выход из логов: Ctrl+C.

**Обновить код на сервере** (на маке):
```bash
cd "/Users/kleshny/ВШЭ"
rsync -avz --exclude venv --exclude .venv --exclude .env --exclude .git --exclude .DS_Store ./LoveStudy/ kleshny@158.160.143.175:~/app/
ssh kleshny@158.160.143.175 "cd ~/app && source venv/bin/activate && pip install -r requirements.txt && sudo systemctl restart lovestudy"
```

**Быстро: добавить БД на проде (если бот пишет «БД не настроена»):**

1. Если кластера PostgreSQL в Yandex Cloud ещё нет: [консоль](https://console.cloud.yandex.ru) → **Managed Service for PostgreSQL** → **Создать кластер**. Регион — как у ВМ. Задай пользователя и пароль БД, запомни их. В карточке кластера нажми **Подключиться** и скопируй строку (вид: `postgresql://user:password@host:6432/dbname?sslmode=require`). Хост бери один — первый из списка (основной).
2. По SSH на сервер скачай сертификат (один раз):  
   `mkdir -p ~/.postgresql && wget -q -O ~/.postgresql/root.crt "https://storage.yandexcloud.net/cloud-certs/CA.pem" && chmod 0644 ~/.postgresql/root.crt`
3. Открой `.env`:  
   `nano ~/app/.env`  
   Добавь строку (подставь свою строку из п.1, пароль без кавычек):  
   `DATABASE_URL=postgresql://user:ПАРОЛЬ@хост:6432/имя_бд?sslmode=require`
4. Сохрани: Ctrl+O, Enter, Ctrl+X.
5. Перезапусти бота:  
   `sudo systemctl restart lovestudy`

**Подключить БД (Yandex Managed PostgreSQL):**

Инструкция на сайте Yandex рассчитана на **psycopg2** и два хоста (основной + реплика). Наш бот использует **asyncpg** — делаем так.

1. **Сертификат для SSL.** Выполни на сервере по SSH (один раз):
   ```bash
   mkdir -p ~/.postgresql && \
   wget "https://storage.yandexcloud.net/cloud-certs/CA.pem" \
        --output-document ~/.postgresql/root.crt && \
   chmod 0644 ~/.postgresql/root.crt
   ```
   Бот при подключении будет использовать этот сертификат для проверки (verify-full).

2. **Один хост в строке подключения.** В инструкции Yandex два хоста — для бота нужен **один**, основной (read-write). Обычно это первый: `rc1b-6iuogd6tvj4aoqf0.mdb.yandexcloud.net`. Строка для `.env`:
   ```
   postgresql://user1:ТВОЙ_ПАРОЛЬ@rc1b-6iuogd6tvj4aoqf0.mdb.yandexcloud.net:6432/db1?sslmode=require
   ```
   Подставь свой пароль вместо `ТВОЙ_ПАРОЛЬ`. Имя пользователя и БД (`user1`, `db1`) — как в консоли Yandex.

3. **Добавить в .env на сервере:**
   ```bash
   nano ~/app/.env
   ```
   В файле должны быть (пароль и хост — свои):
   ```
   BOT_TOKEN=твой_токен
   DATABASE_URL=postgresql://user1:ТВОЙ_ПАРОЛЬ@rc1b-6iuogd6tvj4aoqf0.mdb.yandexcloud.net:6432/db1?sslmode=require
   ```
   Сохрани: Ctrl+O, Enter, Ctrl+X.

4. **Перезапустить бота:**
   ```bash
   sudo systemctl restart lovestudy
   ```
   При старте бот вызовет `init_db()` и создаст таблицы по моделям из `db/models.py` (пользователи, предметы, дедлайны, помодоро и т.д.).

**Про psycopg2 из инструкции Yandex:** `pip3 install psycopg2-binary` и пример с `psycopg2.connect()` — для синхронного подключения (проверка из консоли или своих скриптов). Для самого бота это не нужно: бот уже использует asyncpg из `requirements.txt`.

---

## 1. Виртуальная машина

- **Compute Cloud** → Создать ВМ.
- Образ: Ubuntu 22.04 или 24.04 LTS. Ресурсы по гранту (2 vCPU, 2 ГБ — обычно хватает). Диск 10–15 ГБ.
- Сеть: либо внешний IP, либо NAT (исходящий интернет), чтобы бот мог ходить в Telegram.
- Добавь SSH-ключ. **Подключение:** в консоли открой ВМ → Обзор → блок «Подключиться с помощью SSH-клиента» — там будет готовая команда. Сейчас: `ssh kleshny@158.160.143.175`. Если логин или IP другие — используй команду из консоли, иначе будет `Permission denied (publickey)`.

## 2. Установка на сервере

```bash
sudo apt update && sudo apt install -y python3 python3-venv python3-pip git
mkdir -p ~/app && cd ~/app
```

Залить код (с мака из папки `ВШЭ`, внутри неё лежит `LoveStudy`):

```bash
cd "/Users/kleshny/ВШЭ"
rsync -avz --exclude venv --exclude .venv --exclude .env --exclude .git --exclude .DS_Store ./LoveStudy/ kleshny@158.160.143.175:~/app/
```

На ВМ:

```bash
cd ~/app
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env && nano .env   # BOT_TOKEN, при необходимости DATABASE_URL
```

Проверка:

```bash
python3 -m bot
# В Telegram: /start. Остановка: Ctrl+C.
```

**Важно: один экземпляр на один токен.** С одним и тем же `BOT_TOKEN` может работать только один процесс с long polling. Если бот запущен и на сервере, и у тебя в терминале (или в двух терминалах) — Telegram вернёт `409 Conflict: make sure that only one bot instance is running`. Что делать: остановить все лишние (Ctrl+C в каждом терминале, где крутится бот), оставить один запуск — либо только на сервере (через systemd), либо только локально для разработки.

## 3. Запуск в фоне (systemd)

Готовый юнит лежит в репозитории: `deploy/lovestudy.service` — после `rsync` можно поставить так:  
`sudo cp ~/app/deploy/lovestudy.service /etc/systemd/system/lovestudy.service`.

Файл `/etc/systemd/system/lovestudy.service` (пользователь `kleshny`, приложение в `~/app`):

```ini
[Unit]
Description=LoveStudy Telegram Bot
After=network.target

[Service]
Type=simple
User=kleshny
WorkingDirectory=/home/kleshny/app
ExecStart=/home/kleshny/app/venv/bin/python3 -m bot
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Команды:

```bash
sudo systemctl daemon-reload
sudo systemctl enable lovestudy && sudo systemctl start lovestudy
sudo systemctl status lovestudy
```

Логи: `journalctl -u lovestudy -f`.

## 4. База данных (Managed PostgreSQL) — по шагам

Кластер и ВМ должны быть в **одной облачной сети** (у тебя `default`), зона ВМ **ru-central1-d** — кластер создавай в **той же зоне** и с подсетью в **этой же зоне**.

### 4.1. Узнать CIDR подсети ВМ (для правила файрвола)

1. Консоль Yandex → **Virtual Private Cloud** → **Подсети**.
2. Найди подсеть в зоне **ru-central1-d** (та, к которой привязана ВМ с адресом `10.131.0.21`).
3. Запомни **CIDR**, например `10.131.0.0/24` (у тебя может отличаться — смотри в консоли).

### 4.2. Создать кластер

1. **Managed Service for PostgreSQL** → **Создать кластер**.
2. Версия **15** или **16**, класс хоста **минимальный**, диск по умолчанию.
3. **Сеть** → `default`, **подсеть** → в зоне `ru-central1-d` (как у ВМ).
4. Задай **имя БД**, **имя пользователя**, **пароль** (сохрани в надёжное место).
5. **Группы безопасности** кластера: нужно разрешить входящий трафик с ВМ:
   - либо в SG кластера правило **входящее TCP 6432** (и при необходимости **5432**) **источник** = CIDR подсети из п. 4.1;
   - либо источник = **группа безопасности**, которая назначена на твою ВМ (если так удобнее в интерфейсе).
6. Создай кластер и дождись статуса **Running**.

### 4.3. Строка подключения

1. Открой кластер → **Подключиться** / хосты.
2. Возьми **один** FQDN **основного (master) хоста** и порт **6432** (пул соединений).
3. В `~/app/.env` на сервере добавь одну строку (подставь свои значения; спецсимволы в пароле — [URL-encode](https://www.urlencoder.org/)):

```env
DATABASE_URL=postgresql://ИМЯ_ПОЛЬЗОВАТЕЛЯ:ПАРОЛЬ@мастер-хост.mdb.yandexcloud.net:6432/ИМЯ_БД?sslmode=require
```

### 4.4. Сертификат на ВМ (один раз)

По SSH на сервере:

```bash
mkdir -p ~/.postgresql && wget -q -O ~/.postgresql/root.crt "https://storage.yandexcloud.net/cloud-certs/CA.pem" && chmod 0644 ~/.postgresql/root.crt
```

### 4.5. Перезапуск бота

- Если через **systemd**: `sudo systemctl restart lovestudy`
- Если вручную: останови процесс (`Ctrl+C`), снова `cd ~/app && source venv/bin/activate && python3 -m bot`

В логах должно быть сообщение про **session_factory**, без `DATABASE_URL не задан`. Таблицы создаются при старте через `init_db()` в коде.

### 4.6. Если не коннектится

- **Timeout / no route** — проверь SG кластера и CIDR подсети ВМ.
- **SSL** — файл `~/.postgresql/root.crt` и `sslmode=require` в URL.
- **Authentication failed** — логин, пароль, имя БД как в консоли кластера.

## 5. Обновление кода

С мака:

```bash
cd "/Users/kleshny/ВШЭ"
rsync -avz --exclude venv --exclude .venv --exclude .env --exclude .git --exclude .DS_Store ./LoveStudy/ kleshny@158.160.143.175:~/app/
ssh kleshny@158.160.143.175 "cd ~/app && source venv/bin/activate && pip install -r requirements.txt && sudo systemctl restart lovestudy"
```

Либо на ВМ: `git pull`, затем `pip install -r requirements.txt` и `sudo systemctl restart lovestudy`.
