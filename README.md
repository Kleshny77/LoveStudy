# LoveStudy

Telegram-бот для учёбы: материалы и предметы, викторины по тексту, дедлайны с напоминаниями, помодоро, профиль и друзья. Экраны и сценарии описаны в [docs/screens.md](docs/screens.md).

## Быстрый старт (локально)

1. **Токен:** в Telegram открой @BotFather → `/newbot` (или `/mybots` → выбери бота → API Token).
2. **Виртуальное окружение:** используй `venv` только внутри папки проекта `LoveStudy`, не смешивай с чужим `.venv` из родительских каталогов.

```bash
cd LoveStudy
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

В `.env` укажи `BOT_TOKEN=...`. Для сохранения данных в PostgreSQL добавь `DATABASE_URL=...` (см. [docs/deploy.md](docs/deploy.md)).

3. **Запуск:**

```bash
python3 -m bot
```

В Telegram открой бота и отправь `/start`.

**Один экземпляр на токен:** одновременно может работать только один процесс с long polling (сервер или локально). Иначе в логах будет `409 Conflict` — останови лишние копии (Ctrl+C или `systemctl stop` на сервере).

## Структура проекта

```
LoveStudy/
  bot/           # точка входа: python -m bot, Application
  config.py      # настройки из .env
  handlers/      # Telegram: update → сервис → ответ
  services/      # тексты, клавиатуры, сценарии
  db/            # SQLAlchemy: подключение, модели, репозитории
  ai/            # генерация викторин (LLM)
  deploy/        # systemd-юнит для продакшена (см. docs/deploy.md)
  scripts/       # вспомогательные скрипты (диагностика и т.д.)
  docs/          # деплой, экраны, аналитика
```

События для графиков пишутся в PostgreSQL. **Минимум рук:** на ВМ `bash scripts/setup_metabase.sh`, на Mac `bash scripts/metabase_tunnel.sh`, дальше мастер Metabase в браузере — подробно **[docs/analytics.md](docs/analytics.md)**.

## Деплой и база данных

Продакшен на Yandex Cloud (ВМ + опционально Managed PostgreSQL): **[docs/deploy.md](docs/deploy.md)**. Там же — юнит `deploy/lovestudy.service`, `rsync`, настройка `DATABASE_URL` и групп безопасности.

### Короткий чеклист продакшена

1. Локально бот отвечает на `/start` с заполненным `.env`.
2. На ВМ (Ubuntu 22.04/24.04): код в `~/app`, venv, `pip install -r requirements.txt`, свой `~/app/.env` (не копируется через `rsync`).
3. **Команды `systemctl`, пути `/home/kleshny/...` и установка юнита выполняются на сервере по SSH**, не на Mac — на macOS нет `systemctl`, а путь `/home/kleshny` существует только на ВМ.
4. После `rsync` проверь, что на сервере есть `~/app/deploy/lovestudy.service`; если файла нет — повтори выкладку или создай юнит вручную (см. docs/deploy.md).
5. Включи сервис: `sudo systemctl enable --now lovestudy`, проверь `sudo systemctl status lovestudy`.
6. БД: кластер в той же VPC, правило SG на **TCP 6432** с подсети ВМ, в `.env` — `DATABASE_URL` и сертификат `~/.postgresql/root.crt` на ВМ.
