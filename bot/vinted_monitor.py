import asyncio
import logging
import aiohttp
from bot.vinted_parser import VintedParser

logger = logging.getLogger(__name__)


class VintedMonitor:

  def __init__(self, bot, config):
    self.bot = bot
    self.config = config
    self.parser = VintedParser()
    self.seen_items = set()
    self.rates = {"EUR": 100.0, "PLN": 23.0}

  async def update_rates(self):
    """Получение актуальных курсов валют к рублю."""
    try:
      async with aiohttp.ClientSession() as session:
        async with session.get(
            "https://www.cbr-xml-daily.ru/daily_json.js", timeout=10
        ) as resp:
          if resp.status == 200:
            data = await resp.json(content_type=None)
            valute = data.get("Valute", {})
            if "EUR" in valute:
              self.rates["EUR"] = float(valute["EUR"]["Value"])
            if "PLN" in valute:
              self.rates["PLN"] = float(valute["PLN"]["Value"]) / float(
                  valute["PLN"]["Nominal"]
              )
            logger.info(f"Обновлены курсы валют: {self.rates}")
    except Exception as e:
      logger.warning(
          f"Не удалось обновить курсы валют, используются стандартные: {e}"
      )

  def convert_to_rub(self, price_str: str, currency: str) -> float:
    try:
      amount = float(price_str)
      rate = self.rates.get(currency.upper(), self.rates["EUR"])
      return round(amount * rate, 2)
    except Exception:
      return 0.0

  async def start(self):
    logger.info("Запуск мониторинга Vinted...")
    await self.update_rates()

    rate_update_counter = 0

    while True:
      try:
        search_urls = self.config.get("search_urls", [])
        channel_ids = self.config.get("channel_ids", [])
        delay = self.config.get("refresh_delay", 5)

        for url in search_urls:
          # Запуск парсинга в синхронном потоке для curl_cffi
          items, search_text = await asyncio.to_thread(
              self.parser.fetch_items, url
          )

          for item in items:
            item_id = item["id"]
            if not item_id or item_id in self.seen_items:
              continue

            self.seen_items.add(item_id)

            # Формирование карточки
            price_rub = self.convert_to_rub(
                item["price"], item["currency"]
            )
            caption = (
                f"👕 <b>{item['title']}</b>\n\n"
                f"🏷 <b>Бренд:</b> {item['brand']}\n"
                f"📏 <b>Размер:</b> {item['size']}\n"
                f"💰 <b>Цена:</b> {item['price']} {item['currency']} (~{price_rub} RUB)\n\n"
                f"🔗 <a href='{item['url']}'>Открыть на Vinted</a>"
            )

            for channel_id in channel_ids:
              try:
                if item["photo_url"]:
                  await self.bot.send_photo(
                      chat_id=channel_id,
                      photo=item["photo_url"],
                      caption=caption,
                      parse_mode="HTML",
                  )
                else:
                  await self.bot.send_message(
                      chat_id=channel_id,
                      text=caption,
                      parse_mode="HTML",
                      disable_web_page_preview=False,
                  )
              except Exception as send_err:
                logger.error(
                    f"Ошибка отправки сообщения в {channel_id}: {send_err}"
                )

          await asyncio.sleep(delay)

        # Периодическое обновление курсов каждые ~100 циклов
        rate_update_counter += 1
        if rate_update_counter >= 100:
          await self.update_rates()
          rate_update_counter = 0

      except Exception as e:
        logger.error(f"Ошибка в цикле мониторинга: {e}")
        await asyncio.sleep(10)
