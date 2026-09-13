import logging
from typing import Dict, List, Optional
from urllib.parse import parse_qsl, urlparse
from curl_cffi import requests

logger = logging.getLogger(__name__)


class VintedAPI:

  def __init__(self, country_code: str = ".de"):
    self.country_code = country_code
    self.base_url = f"https://www.vinted{country_code}"
    # Используем имитацию браузера Chrome для обхода защит
    self.session = requests.Session(impersonate="chrome120")
    self._init_session()

  def _init_session(self, url: Optional[str] = None):
    """Инициализирует сессию и получает cookies с главной страницы"""
    target_url = url if url else self.base_url
    try:
      headers = {
          "User-Agent": (
              "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
              "AppleWebKit/537.36 (KHTML, like Gecko) "
              "Chrome/120.0.0.0 Safari/537.36"
          ),
          "Accept": (
              "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
          ),
          "Accept-Language": "en-US,en;q=0.9",
      }
      self.session.get(target_url, headers=headers, timeout=10)
    except Exception as e:
      logger.error(f"Ошибка инициализации сессии Vinted: {e}")

  async def search_by_url(self, url: str) -> List[Dict]:
    """Принимает прямую ссылку из браузера со всеми фильтрами и запрашивает API Vinted"""
    try:
      parsed_url = urlparse(url)

      # Извлекаем домен (.pl, .de, .fr и т.д.)
      domain = parsed_url.netloc.replace("www.vinted", "")
      if not domain:
        domain = self.country_code
      base_url = f"https://www.vinted{domain}"

      # Извлекаем ВСЕ параметры из URL через список кортежей.
      # Это критически важно, чтобы не затирались массивы параметров типа catalog[] и size_id[]
      params_list = parse_qsl(parsed_url.query)
      param_keys = [k for k, v in params_list]

      # Добавляем сортировку по новизне и лимит, если их нет
      if "order" not in param_keys:
        params_list.append(("order", "newest_first"))
      if "page" not in param_keys:
        params_list.append(("page", "1"))
      if "per_page" not in param_keys:
        params_list.append(("per_page", "10"))

      headers = {
          "Host": f"www.vinted{domain}",
          "accept": "application/json, text/plain, */*",
          "accept-language": "en-US,en;q=0.9",
          "user-agent": (
              "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
              "AppleWebKit/537.36 (KHTML, like Gecko) "
              "Chrome/120.0.0.0 Safari/537.36"
          ),
      }

      api_endpoint = f"{base_url}/api/v2/catalog/items"
      response = self.session.get(
          api_endpoint, params=params_list, headers=headers, timeout=10
      )

      # Если получили ошибку доступа, пробуем обновить куки и повторить запрос
      if response.status_code in (401, 403):
        self._init_session(base_url)
        response = self.session.get(
            api_endpoint, params=params_list, headers=headers, timeout=10
        )

      response.raise_for_status()
      data = response.json()

      items = []
      for item in data.get("items", []):
        photos = item.get("photos", [])
        image_url = photos[0].get("url") if photos else None

        # Записываем обработанную картинку и домен прямо в словарь товара
        item["image_url"] = image_url
        item["domain"] = domain
        items.append(item)

      return items
    except Exception as e:
      logger.error(f"Ошибка запроса к API по URL {url}: {str(e)}")
      return []
