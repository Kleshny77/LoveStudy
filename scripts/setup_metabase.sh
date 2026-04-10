#!/usr/bin/env bash
# Запускать НА ВМ по SSH (один раз). Ставит Docker при необходимости и поднимает Metabase
# только на localhost:3000 (снаружи порт не открыт).
set -euo pipefail

docker_wrap() {
  if docker info &>/dev/null; then
    docker "$@"
  elif sudo docker info &>/dev/null; then
    sudo docker "$@"
  else
    echo ">>> Устанавливаю docker.io (нужен sudo)..."
    sudo apt-get update -qq
    sudo apt-get install -y docker.io
    sudo docker "$@"
  fi
}

echo ">>> Скачиваю образ Metabase (первый раз может занять 1–2 минуты)..."
docker_wrap pull metabase/metabase:latest

if docker_wrap ps -a --format '{{.Names}}' 2>/dev/null | grep -qx metabase; then
  echo ">>> Удаляю старый контейнер metabase..."
  docker_wrap rm -f metabase
fi

echo ">>> Запускаю Metabase..."
# --network host: исходящие подключения к PostgreSQL идут так же, как с хоста (как psql).
# Иначе bridge-режим иногда даёт «всё ок в psql, Metabase не коннектится».
# Слушаем только localhost на ВМ (туннель с Mac без изменений).
docker_wrap run -d --name metabase --restart unless-stopped \
  --network host \
  -e MB_JETTY_HOST=127.0.0.1 \
  -e MB_JETTY_PORT=3000 \
  metabase/metabase:latest

echo ""
echo "OK: Metabase слушает на этой ВМ 127.0.0.1:3000"
echo ""
echo "Важно: контейнер пересоздан — внутренние данные Metabase (админ, сохранённые БД) сброшены."
echo "В браузере снова пройди мастер настройки и добавь PostgreSQL (host/port/db/user/password, SSL require, JDBC: prepareThreshold=0)."
echo ""
echo "Дальше на Mac (в другом терминале), из папки LoveStudy:"
echo "  bash scripts/metabase_tunnel.sh"
echo "Потом в браузере: http://localhost:3000  — регистрация админа и Add database (данные из ~/app/.env)."
