#!/bin/bash
# Диагностика бота на сервере. Запуск: ./scripts/diagnose.sh
# Или: bash scripts/diagnose.sh

# Переопределение: export LOVESTUDY_SSH=user@ip
HOST="${LOVESTUDY_SSH:-kleshny@158.160.143.175}"

echo "=== 1. Статус сервиса lovestudy ==="
ssh $HOST "sudo systemctl status lovestudy --no-pager" 2>/dev/null || echo "Не удалось получить статус"

echo ""
echo "=== 2. Последние 80 строк логов ==="
ssh $HOST "sudo journalctl -u lovestudy -n 80 --no-pager -q" 2>/dev/null || echo "Не удалось получить логи"

echo ""
echo "=== 3. Проверка .env (BOT_TOKEN и DATABASE_URL) ==="
ssh $HOST "test -f ~/app/.env && grep -E '^BOT_TOKEN=|^DATABASE_URL=' ~/app/.env | sed 's/=.*/=***/' || echo '.env не найден!'" 2>/dev/null

echo ""
echo "=== 4. Запуск бота вручную (5 сек) — покажет ошибки при старте ==="
ssh $HOST "cd ~/app && source venv/bin/activate && timeout 5 python -m bot 2>&1 || true" 2>/dev/null
