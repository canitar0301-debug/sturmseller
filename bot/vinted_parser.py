import logging
from urllib.parse import parse_qs, urlparse
from curl_cffi import requests

logger = logging.getLogger(__name__)


class VintedParser:

  def __init__(self):
    self.session = requests.Session(impersonate="chrome120")

  def _get_domain_and_params(self, url: str):
    parsed = urlparse(url)
    domain = parsed.netloc
    params = parse_qs(parsed.query)
    return domain, params

  def fetch_items(self, search_url: str) -> list:
    domain, params = self._get_domain_and_params(search_url)

    api_params = {}
    for k, v in params.items():
      if k.endswith("[]"):
        api_params[k] = v
      else:
        api_params[k] = v[0] if v else ""

    api_url = f"https://{domain}/api/v2/catalog/items"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            " (KHTML, Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json, text/plain, */*",
    }

    try:
      self.session.get(f"https://{domain}", headers=headers, timeout=10)
      response = self.session.get(
          api_url, params=api_params, headers=headers, timeout=10
      )

      if response.status_code == 200:
        data = response.json()
        items = data.get("items", [])
        parsed_items = []
        for item in items:
          parsed_items.append({
              "id": item.get("id"),
              "title": item.get("title", "Без названия"),
              "price": item.get("price", {}).get("amount", "0"),
              "currency": item.get("price", {}).get(
                  "currency_code", "EUR"
              ),
              "size": item.get("size_title", "N/A"),
              "brand": item.get("brand_title", "N/A"),
              "url": item.get("url", ""),
              "photo_url": (
                  item.get("photos", [{}])[0].get("url")
                  if item.get("photos")
                  else None
              ),
          })
        return parsed_items
      else:
        logger.error(f"Ошибка Vinted API ({response.status_code})")
        return []
    except Exception as e:
      logger.error(f"Ошибка парсинга Vinted ({search_url}): {e}")
      return []
