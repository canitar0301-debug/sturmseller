import logging
import re
from urllib.parse import parse_qs, urlparse
from curl_cffi import requests

logger = logging.getLogger(__name__)


class VintedParser:

  def __init__(self):
    self.session = requests.Session(impersonate="chrome120")
    self.domains_initialized = set()

  def _init_session(self, domain: str):
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            " (KHTML, Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": (
            "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
        ),
        "Accept-Language": "en-US,en;q=0.9",
    }
    try:
      res = self.session.get(f"https://{domain}", headers=headers, timeout=25)
      token = self.session.cookies.get("access_token_web")
      if not token and res.text:
        match = re.search(r'"token":"([^"]+)"', res.text)
        if match:
          token = match.group(1)

      if token:
        self.session.headers["Authorization"] = f"Bearer {token}"

      self.domains_initialized.add(domain)
    except Exception as e:
      logger.error(f"Ошибка инициализации сессии Vinted ({domain}): {e}")

  def _get_domain_and_params(self, url: str):
    parsed = urlparse(url)
    domain = parsed.netloc
    params = parse_qs(parsed.query)
    return domain, params

  def fetch_items(self, search_url: str) -> tuple[list, str]:
    domain, params = self._get_domain_and_params(search_url)

    if domain not in self.domains_initialized:
      self._init_session(domain)

    api_params = {"order": "newest_first"}

    search_text = ""
    for k, v in params.items():
      val = v[0] if v else ""
      if k == "search_text":
        search_text = val
        api_params["search_text"] = val
      elif k in ["catalog[]", "catalog"]:
        api_params["catalog_ids"] = ",".join(v)
      elif k.endswith("[]"):
        clean_key = k[:-2] + "_ids"
        api_params[clean_key] = ",".join(v)
      else:
        api_params[k] = val

    api_url = f"https://{domain}/api/v2/catalog/items"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            " (KHTML, Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json, text/plain, */*",
        "X-Requested-With": "XMLHttpRequest",
    }

    token = self.session.cookies.get("access_token_web")
    if token:
      headers["Authorization"] = f"Bearer {token}"

    try:
      response = self.session.get(
          api_url, params=api_params, headers=headers, timeout=25
      )

      if response.status_code in (401, 404):
        self._init_session(domain)
        token = self.session.cookies.get("access_token_web")
        if token:
          headers["Authorization"] = f"Bearer {token}"
        response = self.session.get(
            api_url, params=api_params, headers=headers, timeout=25
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
        return parsed_items, search_text
      else:
        logger.error(f"Ошибка Vinted API ({response.status_code})")
        return [], search_text
    except Exception as e:
      logger.error(f"Ошибка парсинга Vinted ({search_url}): {e}")
      return [], search_text
