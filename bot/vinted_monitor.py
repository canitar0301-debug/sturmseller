import asyncio
import json
import logging
import os
from bot.currency_converter import CurrencyConverter
from bot.telegram_bot import TelegramBot
from bot.vinted_parser import VintedParser

logger = logging.getLogger(__name__)


class VintedMonitor:

  def __init__(self, config_path: str = "config.json"):
    with open(config_path, "r", encoding="utf-8") as f:
      self.config = json.load(f)

    self.bot = TelegramBot(self.config["token"], self.config["channel_ids"])
    self.parser = VintedParser()
    self.currency_converter = CurrencyConverter()
    self.refresh_delay = self.config.get("refresh_delay", 2)
    self.search_urls = self.config.get("search_urls", [])

    self.seen_items_file = "seen_items.json"
    self.seen_items = self._load_seen_items()

  def _load_seen_items(self):
    if os.path.exists(self.seen_items_file):
      try:
        with open(self.seen_items_file, "r", encoding="utf-8") as f:
          return set(json.load(f))
      except Exception as e:
        logger.error(f"Ошибка чтения {self.seen_items_file}: {e}")
    return set()

  def _save_seen_items(self):
    try:
      with open(self.seen_items_file, "w", encoding="utf-8") as f:
        json.dump(list(self.seen_items), f, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Ошибка сохранения {self.seen_items_file}: {e}")

  async def check_updates(self):
    for url in self.search_urls:
      try:
        items = self.parser.fetch_items(url)
        for item in items:
          item_id = str(item["id"])
          if item_id not in self.seen_items:
            self.seen_items.add(item_id)

            price_rub = self.currency_converter.convert(
                item["price"], item["currency"]
            )
            text = (
                f"<b>{item['title'].upper()}</b>\n\n"
                f"💰 Цена: {item['price']} {item['currency']} (~{price_rub} RUB)\n"
                f"📏 Размер: {item.get('size', 'N/A')}\n"
                f"🏷 Бренд: {item.get('brand', 'N/A')}"
            )

            # Вызов функции отправки через await
            await self.bot.send_message(
                text=text,
                image_url=item.get("photo_url"),
                product_url=item.get("url"),
            )
        self._save_seen_items()
      except Exception as e:
        logger.error(f"Ошибка обработки ссылки {url}: {e}")

  async def start(self):
    logger.info("Запуск мониторинга Vinted...")
    while True:
      await self.check_updates()
      await asyncio.sleep(self.refresh_delay)
