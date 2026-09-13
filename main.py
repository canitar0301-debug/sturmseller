import asyncio
import json
import logging
from api.vinted_api import VintedAPI
from bot.telegram_bot import TelegramBot
from bot.vinted_monitor import VintedMonitor

logging.basicConfig(level=logging.INFO)


def load_config():
  try:
    with open("config/config.json", "r", encoding="utf-8") as f:
      return json.load(f)
  except FileNotFoundError:
    with open("config.json", "r", encoding="utf-8") as f:
      return json.load(f)


async def main():
  config = load_config()

  # Считываем либо новый список channel_ids, либо старый channel_id
  channel_ids = config.get("channel_ids") or config.get("channel_id")

  bot = TelegramBot(token=config.get("token"), chat_ids=channel_ids)

  api = VintedAPI()
  monitor = VintedMonitor(api=api, bot=bot, config=config)

  await monitor.start_monitoring()


if __name__ == "__main__":
  asyncio.run(main())
