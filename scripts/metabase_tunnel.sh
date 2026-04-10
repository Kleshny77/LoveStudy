#!/usr/bin/env bash
# Запускать НА МАКЕ (локально). Открывает SSH-туннель к Metabase на ВМ.
# Переменная LOVESTUDY_SSH переопределяет хост (как в diagnose.sh).
set -euo pipefail

HOST="${LOVESTUDY_SSH:-kleshny@158.160.143.175}"

echo "SSH-туннель: localhost:3000 → ${HOST}:127.0.0.1:3000"
echo "После ввода passphrase окно будет «молчать» — так и должно быть, туннель уже работает."
echo "Открой в браузере: http://localhost:3000  (терминал не закрывай)"
echo "Остановка туннеля: Ctrl+C"
echo ""

exec ssh -o ServerAliveInterval=30 -o ServerAliveCountMax=3 -N -L 3000:127.0.0.1:3000 "$HOST"
