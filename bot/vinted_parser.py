import logging
import re
from urllib.parse import parse_qs, urlparse
from curl_cffi import requests

logger = logging.getLogger(__name__)


class VintedParser:

  def __init__(self):
    # Раздельные сессии для каждого домена (.pl, .de и т.д.)
    self.sessions = {}

  def _get_session(self, domain: str) -> requests.Session:
    if domain not in self.sessions:
      session = requests.Session(impersonate="chrome120")
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
        res = session.get(f"https://{domain}", headers=headers, timeout=25)
        token = session.cookies.get("access_token_web", domain=domain)
        if not token and res.text:
          match = re.search(r'"token":"([^"]+)"', res.text)
          if match:
            token = match.group(1)

        if token:
          session.headers["Authorization"] = f"Bearer {token}"

        self.sessions[domain] = session
      except Exception as e:
        logger.error(f"Ошибка инициализации сессии Vinted ({domain}): {e}")
        return session
    return self.sessions[domain]

  def _get_domain_and_params(self, url: str):
    parsed = urlparse(url)
    domain = parsed.netloc
    params = parse_qs(parsed.query)
    return domain, params

  def fetch_items(self, search_url: str) -> tuple[list, str]:
    domain, params = self._get_domain_and_params(search_url)
    session = self._get_session(domain)

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

    token = session.cookies.get("access_token_web", domain=domain)
    if token:
      headers["Authorization"] = f"Bearer {token}"

    try:
      response = session.get(
          api_url, params=api_params, headers=headers, timeout=25
      )

      if response.status_code in (401, 404):
        if domain in self.sessions:
          del self.sessions[domain]
        session = self._get_session(domain)
        token = session.cookies.get("access_token_web", domain=domain)
        if token:
          headers["Authorization"] = f"Bearer {token}"
        response = session.get(
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
