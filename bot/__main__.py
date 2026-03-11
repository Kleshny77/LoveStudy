# запуск: из корня проекта выполни python -m bot

import logging

from bot.app import run_polling

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

if __name__ == "__main__":
    run_polling()
