import logging
import re
from urllib.parse import parse_qs, urlsplit
from curl_cffi import requests

logger = logging.getLogger(__name__)


class VintedParser:

  def __init__(self):
    # Раздельные сессии для каждого домена (www.vinted.pl, www.vinted.de и т.д.)
    self.sessions = {}

  def _create_session(self, domain: str) -> requests.Session:
    session = requests.Session(impersonate="chrome120")
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            " (KHTML, Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": (
            "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
        ),
        "Accept-Language": "en-US,en;q=0.9,pl;q=0.8,de;q=0.7",
    }

    try:
      # Заходим на главную страницу для получения кук и токенов
      resp = session.get(f"https://{domain}/", headers=headers, timeout=20)

      token = None
      # 1. Попытка получить токен из словаря кук
      cookie_dict = session.cookies.get_dict()
      if "access_token_web" in cookie_dict:
        token = cookie_dict["access_token_web"]

      # 2. Поиск токена в HTML-коде страницы
      if not token and resp.text:
        match = (
            re.search(r'"access_token_web":"([^"]+)"', resp.text)
            or re.search(r'"accessToken":"([^"]+)"', resp.text)
            or re.search(r'"token":"([^"]+)"', resp.text)
        )
        if match:
          token = match.group(1)

      if token:
        session.headers["Authorization"] = f"Bearer {token}"
        logger.info(f"Сессия для {domain} инициализирована (Токен получен)")
      else:
        logger.warning(
            f"Токен не найден для {domain}, продолжение с имеющимися куками"
        )

    except Exception as e:
      logger.error(f"Ошибка при инициализации сессии ({domain}): {e}")

    return session

  def _get_session(
      self, domain: str, force_refresh: bool = False
  ) -> requests.Session:
    if force_refresh or domain not in self.sessions:
      self.sessions[domain] = self._create_session(domain)
    return self.sessions[domain]

  def fetch_items(self, search_url: str) -> tuple[list, str]:
    parsed_url = urlsplit(search_url)
    domain = parsed_url.netloc
    query_params = parse_qs(parsed_url.query)

    session = self._get_session(domain)

    # Нормализация параметров под требование Vinted API /api/v2/catalog/items
    api_params = {
        "order": "newest_first",
        "page": "1",
        "per_page": "96",
    }

    search_text = ""
    for key, vals in query_params.items():
      val = vals[0] if vals else ""
      clean_key = key.replace("[]", "")

      if clean_key == "search_text":
        search_text = val
        api_params["search_text"] = val
      elif clean_key in ["catalog", "catalog_ids"]:
        api_params["catalog_ids"] = ",".join(vals)
      elif key.endswith("[]"):
        api_params[f"{clean_key}_ids"] = ",".join(vals)
      else:
        api_params[key] = val

    api_url = f"https://{domain}/api/v2/catalog/items"
    api_headers = {
        "Accept": "application/json, text/plain, */*",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": search_url,
    }

    try:
      resp = session.get(
          api_url, params=api_params, headers=api_headers, timeout=20
      )

      # Если получили ошибку сессии (401/403/404) — сбрасываем и обновляем сессию
      if resp.status_code in (401, 403, 404):
        logger.warning(
            f"Получен статус {resp.status_code} от {domain}. Пересоздаем"
            " сессию..."
        )
        session = self._get_session(domain, force_refresh=True)
        resp = session.get(
            api_url, params=api_params, headers=api_headers, timeout=20
        )

      if resp.status_code == 200:
        data = resp.json()
        items = data.get("items", [])
        parsed_items = []
        for item in items:
          photos = item.get("photos") or []
          photo_url = (
              photos[0].get("url")
              if photos and isinstance(photos[0], dict)
              else None
          )

          price_val = "0"
          currency_val = "EUR"
          if isinstance(item.get("price"), dict):
            price_val = item.get("price", {}).get("amount", "0")
            currency_val = item.get("price", {}).get("currency_code", "EUR")
          elif item.get("price"):
            price_val = str(item.get("price"))

          parsed_items.append({
              "id": item.get("id"),
              "title": item.get("title", "Без названия"),
              "price": price_val,
              "currency": currency_val,
              "size": item.get("size_title", "N/A"),
              "brand": item.get("brand_title", "N/A"),
              "url": item.get("url", ""),
              "photo_url": photo_url,
          })
        return parsed_items, search_text
      else:
        logger.error(
            f"Ошибка Vinted API ({resp.status_code}) для URL: {search_url} |"
            f" Ответ: {resp.text[:150]}"
        )
        return [], search_text

    except Exception as e:
      logger.error(f"Исключение при запросе к Vinted ({search_url}): {e}")
      return [], search_text
