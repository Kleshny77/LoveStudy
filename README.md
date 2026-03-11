# LoveStudy

Telegram-бот для личных сообщений. Экраны и сценарии добавляются по прототипам.

## Быстрый старт

1. **Токен:** в Telegram открой @BotFather → `/newbot` → имя и username (на `bot`) → скопируй токен.
2. **Окружение:** один venv только внутри папки LoveStudy (не в родительской МАИНОР). Если уже есть `.venv` снаружи — не используй его для этого проекта.

```bash
cd LoveStudy
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

В `.env` пропиши `BOT_TOKEN=...` (токен от BotFather).

3. **Запуск:**

```bash
python3 -m bot
```

В Telegram открой бота и отправь `/start`. (На Windows: `python -m bot`, активация venv — `venv\Scripts\activate`.)

**Один экземпляр:** с одним токеном может работать только один процесс (сервер или локально). Иначе будет `409 Conflict` в логах — останови лишние (Ctrl+C).

## Структура проекта

```
LoveStudy/
  bot/           # точка входа (python -m bot), сборка Application
  config.py      # настройки из .env
  handlers/      # хендлеры: update → сервис → ответ
  services/      # бизнес-логика (тексты, сценарии)
  db/            # БД: подключение и модели (опционально)
  docs/          # документация (деплой и т.п.)
```

## Деплой и БД

Хостинг в Yandex Cloud (ВМ + опционально Managed PostgreSQL): **[docs/deploy.md](docs/deploy.md)**.

### Чеклист: что сделать, чтобы захостить и подключить БД

1. **Локально:** в `.env` есть `BOT_TOKEN`, бот запускается (`python3 -m bot`), в Telegram отвечает на `/start`.
2. **Сервер:** создать ВМ в Yandex Cloud (Ubuntu 22.04), залить код в `~/app`, сделать venv, установить зависимости, скопировать `.env` с `BOT_TOKEN`.
3. **Запуск:** настроить systemd (см. docs/deploy.md), проверить `systemctl status lovestudy`, написать боту — ответ приходит.
4. **БД (по желанию):** создать кластер Managed PostgreSQL в Yandex Cloud, скопировать строку подключения в `.env` на сервере как `DATABASE_URL=postgresql://...`. После добавления моделей в `db/models.py` при старте бота таблицы создадутся автоматически.
