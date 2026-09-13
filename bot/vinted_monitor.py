import asyncio
import json
import logging
import os
import time
import urllib.request

logger = logging.getLogger(__name__)

# Соответствие доменов Vinted и стран
COUNTRY_MAP = {
    ".pl": "ПОЛЬША",
    ".de": "ГЕРМАНИЯ",
    ".fr": "ФРАНЦИЯ",
    ".it": "ИТАЛИЯ",
    ".es": "ИСПАНИЯ",
    ".nl": "НИДЕРЛАНДЫ",
    ".be": "БЕЛЬГИЯ",
    ".cz": "ЧЕХИЯ",
    ".sk": "СЛОВАКИЯ",
    ".lt": "ЛИТВА",
    ".at": "АВСТРИЯ",
    ".co.uk": "ВЕЛИКОБРИТАНИЯ",
    ".uk": "ВЕЛИКОБРИТАНИЯ",
}

# Красивое отображение значков валют
SYMBOL_MAP = {
    "PLN": "zł",
    "EUR": "€",
    "CZK": "Kč",
    "GBP": "£",
    "USD": "$",
    "SEK": "kr",
    "DKK": "kr",
    "HUF": "Ft",
    "RON": "lei",
}


class CurrencyConverter:
  """Получает курсы валют ЦБ РФ и конвертирует суммы в рубли"""

  def __init__(self):
    self.rates = {}
    self.last_update = 0

  def _update_rates(self):
    # Обновляем курсы ЦБ не чаще 1 раза в час
    if time.time() - self.last_update < 3600 and self.rates:
      return

    try:
      url = "https://www.cbr-xml-daily.ru/daily_json.js"
      req = urllib.request.Request(
          url, headers={"User-Agent": "Mozilla/5.0"}
      )
      with urllib.request.urlopen(req, timeout=5) as response:
        data = json.loads(response.read().decode("utf-8"))
        self.rates = data.get("Valute", {})
        self.last_update = time.time()
        logger.info("Курсы ЦБ РФ успешно обновлены")
    except Exception as e:
      logger.error(f"Ошибка при получении курсов ЦБ РФ: {e}")

  def convert_to_rub(self, amount: float, currency_code: str):
    self._update_rates()

    curr_upper = currency_code.upper()
    normalize_map = {
        "ZL": "PLN",
        "ZŁ": "PLN",
        "PLN": "PLN",
        "EUR": "EUR",
        "€": "EUR",
        "CZK": "CZK",
        "KČ": "CZK",
        "GBP": "GBP",
        "£": "GBP",
        "USD": "USD",
        "$": "USD",
    }
    code = normalize_map.get(curr_upper, curr_upper)

    if code in self.rates:
      valute = self.rates[code]
      nominal = valute.get("Nominal", 1)
      value = valute.get("Value", 0)
      if nominal > 0 and value > 0:
        return amount * (value / nominal)
    return None


class VintedMonitor:

  def __init__(self, api, bot, config):
    self.api = api
    self.bot = bot
    self.config = config
    self.seen_file = "seen_items.json"
    self.seen_items = self._load_seen_items()
    self.converter = CurrencyConverter()

  def _load_seen_items(self) -> set:
    """Загружает список ID отправленных товаров из файла"""
    if os.path.exists(self.seen_file):
      try:
        with open(self.seen_file, "r", encoding="utf-8") as f:
          return set(json.load(f))
      except Exception as e:
        logger.error(f"Ошибка чтения {self.seen_file}: {e}")
    return set()

  def _save_seen_items(self):
    """Сохраняет список ID в файл"""
    try:
      ids_to_save = list(self.seen_items)[-5000:]
      with open(self.seen_file, "w", encoding="utf-8") as f:
        json.dump(ids_to_save, f)
    except Exception as e:
      logger.error(f"Ошибка сохранения {self.seen_file}: {e}")

  async def start_monitoring(self):
    """Главный цикл отслеживания"""
    search_urls = self.config.get("search_urls", [])
    refresh_delay = self.config.get("refresh_delay", 2)

    logger.info("🚀 Мониторинг запущен...")

    while True:
      logger.info("🔍 Проверяем новые объявления на Vinted...")

      for url in search_urls:
        items = await self.api.search_by_url(url)

        for item in items:
          item_id = item.get("id")

          # 1. Проверка на дубликаты
          if not item_id or item_id in self.seen_items:
            continue

          # 2. Сохраняем новый ID
          self.seen_items.add(item_id)
          self._save_seen_items()

          # 3. Извлечение параметров товара
          title = item.get("title", "Без названия")

          # Определение страны по домену
          domain = item.get("domain", ".de").lower()
          country_name = COUNTRY_MAP.get(
              domain, domain.replace(".", "").upper()
          )

          # Извлечение размера
          size = item.get("size_title")
          if not size and isinstance(item.get("size"), dict):
            size = item.get("size", {}).get("title")
          size = size or "Не указан"

          # Извлечение цены и парсинг суммы
          price_raw = item.get("price")
          amount = 0.0
          currency_code = "EUR"

          if isinstance(price_raw, dict):
            try:
              amount = float(price_raw.get("amount", 0))
            except (ValueError, TypeError):
              amount = 0.0
            currency_code = str(price_raw.get("currency_code", "EUR"))
          elif price_raw:
            try:
              amount = float(price_raw)
            except (ValueError, TypeError):
              amount = 0.0
            currency_code = str(item.get("currency", "EUR"))

          # Символ для отображения исходной валюты (zł, €, Kč и т.д.)
          curr_upper = currency_code.upper()
          symbol = SYMBOL_MAP.get(curr_upper, currency_code)

          # Конвертация в рубли по курсу ЦБ РФ
          rub_amount = self.converter.convert_to_rub(amount, currency_code)

          if rub_amount is not None:
            # Форматирование рублей (разделитель тысяч — пробел)
            rub_formatted = f"{round(rub_amount):,}".replace(",", " ")
            amount_str = (
                f"{int(amount)}" if amount.is_integer() else f"{amount}"
            )
            price = f"{amount_str} {symbol} = {rub_formatted} ₽"
          elif amount > 0:
            amount_str = (
                f"{int(amount)}" if amount.is_integer() else f"{amount}"
            )
            price = f"{amount_str} {symbol}"
          else:
            price = "Не указана"

          # Ссылка на товар
          item_url = item.get("url", "")
          if item_url and not item_url.startswith("http"):
            item_url = f"https://www.vinted{domain}{item_url}"

          # Форматирование текста
          text = (
              f"🚩 <b>{country_name}</b>\n"
              f"👕 <b>{title}</b>\n"
              f"📏 <b>Размер:</b> {size}\n"
              f"💰 <b>Цена:</b> {price}"
          )
          image_url = item.get("image_url")

          # 4. Отправка в Telegram
          self.bot.send_message(
              text=text, image_url=image_url, product_url=item_url
          )

          await asyncio.sleep(1)

      await asyncio.sleep(refresh_delay * 60)
