#!/usr/bin/env bash
# Проверка доступа к PostgreSQL с ВМ (те же условия, что у бота).
# Запуск на сервере: cd ~/app && bash scripts/test_pg_connection.sh
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ ! -f .env ]]; then
  echo "Нет файла .env в $(pwd)"
  exit 1
fi
set -a
# shellcheck disable=SC1091
source .env
set +a
if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "DATABASE_URL пуст в .env"
  exit 1
fi
URL="${DATABASE_URL}"
URL="${URL//postgresql+asyncpg:\/\//postgresql:\/\/}"
export PGSSLROOTCERT="${PGSSLROOTCERT:-$HOME/.postgresql/root.crt}"
if [[ ! -f "$PGSSLROOTCERT" ]]; then
  echo "Нет $PGSSLROOTCERT — скачай CA: https://storage.yandexcloud.net/cloud-certs/CA.pem"
  exit 1
fi
if ! command -v psql &>/dev/null; then
  echo "Ставлю postgresql-client..."
  sudo apt-get update -qq && sudo apt-get install -y postgresql-client
fi
echo "Проверка: psql → select 1 (пароль в URL не показывается)"
psql "$URL" -c "select 1 as ok;"
