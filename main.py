import asyncio
import json
import logging
import os
import sys
from aiogram import Bot
from bot.vinted_monitor import VintedMonitor

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

CONFIG_PATH = "config.json"


def load_config():
  if not os.path.exists(CONFIG_PATH):
    raise FileNotFoundError(f"Файл {CONFIG_PATH} не найден!")
  with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    return json.load(f)


async def main():
  config = load_config()
  bot = Bot(token=config["token"])

  monitor = VintedMonitor(bot, config)
  await monitor.start()


if __name__ == "__main__":
  try:
    asyncio.run(main())
  except (KeyboardInterrupt, SystemExit):
    logging.info("Бот остановлен.")
