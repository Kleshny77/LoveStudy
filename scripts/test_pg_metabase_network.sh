#!/usr/bin/env bash
# На ВМ: проверка PostgreSQL из того же network namespace, что и контейнер Metabase.
# Если здесь ошибка, а «обычный» psql на хосте — ok, проблема в сети Docker, не в JDBC.
set -euo pipefail

APP_DIR="${LOVESTUDY_APP_DIR:-$HOME/app}"
CONTAINER="${METABASE_CONTAINER:-metabase}"

docker_wrap() {
  if docker info &>/dev/null; then
    docker "$@"
  elif sudo docker info &>/dev/null; then
    sudo docker "$@"
  else
    echo "Docker недоступен (нужен docker или sudo docker)." >&2
    exit 1
  fi
}

if ! docker_wrap ps --format '{{.Names}}' 2>/dev/null | grep -qx "$CONTAINER"; then
  echo "Контейнер «$CONTAINER» не запущен. Сначала: bash ~/app/scripts/setup_metabase.sh" >&2
  exit 1
fi

if [[ ! -f "$APP_DIR/.env" ]]; then
  echo "Нет файла $APP_DIR/.env" >&2
  exit 1
fi

set -a
# shellcheck disable=SC1090
source "$APP_DIR/.env"
set +a

URL="${DATABASE_URL/postgresql+asyncpg/postgresql}"

echo ">>> psql из network namespace контейнера «$CONTAINER» (как исходящий трафик Metabase)"
docker_wrap run --rm --network "container:$CONTAINER" postgres:16-bookworm \
  psql "$URL" -c "select 1 as ok;"
