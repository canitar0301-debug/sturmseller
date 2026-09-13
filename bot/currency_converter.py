import logging
import xml.etree.ElementTree as ET
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)


class CurrencyConverter:

  def __init__(self):
    self.rates = {"RUB": 1.0}
    self.update_rates()

  def update_rates(self):
    try:
      url = "https://www.cbr.ru/scripts/XML_daily.asp"
      req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
      with urlopen(req) as response:
        xml_data = response.read()

      root = ET.fromstring(xml_data)
      for valute in root.findall("Valute"):
        char_code = valute.find("CharCode").text
        nominal = float(valute.find("Nominal").text.replace(",", "."))
        value = float(valute.find("Value").text.replace(",", "."))
        self.rates[char_code] = value / nominal
    except Exception as e:
      logger.error(f"Ошибка получения курсов ЦБ РФ: {e}")
      # Запасные фиксированные курсы
      self.rates.update({
          "PLN": 23.0,
          "EUR": 100.0,
          "USD": 90.0,
          "GBP": 115.0,
          "CZK": 4.0,
          "SEK": 8.5,
      })

  def convert(self, amount: float, currency: str) -> float:
    currency = currency.upper()
    if currency not in self.rates:
      self.update_rates()

    rate = self.rates.get(currency, 1.0)
    return round(float(amount) * rate, 2)
