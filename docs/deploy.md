# Деплой в Yandex Cloud

Инструкция: ВМ для бота + по желанию Managed PostgreSQL. Грант — [консоль Yandex Cloud](https://console.cloud.yandex.ru).

---

## Готовые команды (kleshny, 158.160.190.46)

Ниже всё под твой случай: пользователь `kleshny`, IP `158.160.190.46`. Копируй и вставляй.

**Подключиться по SSH:**
```bash
ssh kleshny@158.160.190.46
```

**Залить код на сервер** (выполнять на маке, из папки `Майнор`, где лежит папка `LoveStudy`):
```bash
cd "/Users/sass-artem/hse/Майнор"
rsync -avz --exclude venv --exclude .venv --exclude .env ./LoveStudy/ kleshny@158.160.190.46:~/app/
```

**Пункт 3 — systemd (бот в фоне).** На сервере по SSH выполни по порядку.

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

Если статус `active (running)` — бот крутится в фоне. Логи смотреть так:
```bash
journalctl -u lovestudy -f
```
Выход из логов: Ctrl+C.

**Обновить код на сервере** (на маке, из папки Майнор):
```bash
cd "/Users/sass-artem/hse/Майнор"
rsync -avz --exclude venv --exclude .venv --exclude .env ./LoveStudy/ kleshny@158.160.190.46:~/app/
ssh kleshny@158.160.190.46 "cd ~/app && source venv/bin/activate && pip install -r requirements.txt && sudo systemctl restart lovestudy"
```

**Быстро: добавить БД на проде (если бот пишет «БД не настроена»):**

1. Если кластера PostgreSQL в Yandex Cloud ещё нет: [консоль](https://console.cloud.yandex.ru) → **Managed Service for PostgreSQL** → **Создать кластер**. Регион — как у ВМ. Задай пользователя и пароль БД, запомни их. В карточке кластера нажми **Подключиться** и скопируй строку (вид: `postgresql://user:password@host:6432/dbname?sslmode=require`). Хост бери один — первый из списка (основной).
2. По SSH на сервер скачай сертификат (один раз):  
   `mkdir -p ~/.postgresql && wget -q -O ~/.postgresql/root.crt "https://storage.yandexcloud.net/cloud-certs/CA.pem" && chmod 0655 ~/.postgresql/root.crt`
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
   chmod 0655 ~/.postgresql/root.crt
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
   При старте бот вызовет `init_db()` и создаст таблицы по моделям из `db/models.py`. Пока там только `Base` — таблиц нет; когда добавишь модели, они появятся после рестарта.

**Про psycopg2 из инструкции Yandex:** `pip3 install psycopg2-binary` и пример с `psycopg2.connect()` — для синхронного подключения (проверка из консоли или своих скриптов). Для самого бота это не нужно: бот уже использует asyncpg из `requirements.txt`.

---

## 1. Виртуальная машина

- **Compute Cloud** → Создать ВМ.
- Образ: Ubuntu 22.04 LTS. Ресурсы по гранту (2 vCPU, 2 ГБ — обычно хватает). Диск 10–15 ГБ.
- Сеть: либо внешний IP, либо NAT (исходящий интернет), чтобы бот мог ходить в Telegram.
- Добавь SSH-ключ. **Подключение:** в консоли открой ВМ → Обзор → блок «Подключиться с помощью SSH-клиента» — там будет готовая команда. Пользователь может быть не `ubuntu`, а из имени ключа (например `kleshny`), т.е. команда вида `ssh -l kleshny <IP>` или `ssh kleshny@<IP>`. Используй именно её, иначе будет Permission denied (publickey).

## 2. Установка на сервере

```bash
sudo apt update && sudo apt install -y python3 python3-venv python3-pip git
mkdir -p ~/app && cd ~/app
```

Залить код (с мака из папки с LoveStudy). Подставь пользователя и IP из консоли (как в команде SSH):

```bash
rsync -avz --exclude venv --exclude .venv --exclude .env ./LoveStudy/ <USER>@<IP_ВМ>:~/app/
# пример: rsync -avz --exclude venv --exclude .venv --exclude .env ./LoveStudy/ kleshny@158.160.190.46:~/app/
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

Файл `/etc/systemd/system/lovestudy.service`. Замени `<USER>` на своего пользователя ВМ (тот же, что в SSH, например `kleshny`):

```ini
[Unit]
Description=LoveStudy Telegram Bot
After=network.target

[Service]
Type=simple
User=<USER>
WorkingDirectory=/home/<USER>/app
ExecStart=/home/<USER>/app/venv/bin/python3 -m bot
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

## 4. База данных (Managed PostgreSQL)

- В консоли: **Managed Service for PostgreSQL** → Создать кластер (PostgreSQL 15/16, минимальный класс).
- Задать пользователя и пароль, разрешить доступ из подсети ВМ (или из интернета).
- В карточке БД скопировать строку подключения и в `.env` на сервере добавить:
  `DATABASE_URL=postgresql://user:password@host:6432/dbname?sslmode=require`
- В коде (`db.connection`) строка приводится к `postgresql+asyncpg://`. При старте бота вызывается `init_db()` — таблицы по моделям создадутся автоматически.

## 5. Обновление кода

С мака (из каталога, где лежит LoveStudy). Подставь своего пользователя и IP:

```bash
rsync -avz --exclude venv --exclude .venv --exclude .env ./LoveStudy/ <USER>@<IP>:~/app/
ssh <USER>@<IP> "cd ~/app && source venv/bin/activate && pip install -r requirements.txt && sudo systemctl restart lovestudy"
```

Либо на ВМ: `git pull`, затем `pip install -r requirements.txt` и `sudo systemctl restart lovestudy`.
