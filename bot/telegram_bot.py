import logging
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode

logger = logging.getLogger(__name__)


class TelegramBot:

  def __init__(self, token: str, channel_ids: list):
    self.bot = Bot(token=token)
    self.channel_ids = channel_ids

  async def send_message(
      self, text: str, image_url: str = None, product_url: str = None
  ):
    reply_markup = None
    if product_url:
      keyboard = [
          [InlineKeyboardButton("🔗 Перейти к товару", url=product_url)]
      ]
      reply_markup = InlineKeyboardMarkup(keyboard)

    for channel_id in self.channel_ids:
      try:
        if image_url:
          await self.bot.send_photo(
              chat_id=channel_id,
              photo=image_url,
              caption=text,
              parse_mode=ParseMode.HTML,
              reply_markup=reply_markup,
          )
        else:
          await self.bot.send_message(
              chat_id=channel_id,
              text=text,
              parse_mode=ParseMode.HTML,
              reply_markup=reply_markup,
          )
      except Exception as e:
        logger.error(f"Ошибка отправки в Telegram ({channel_id}): {e}")
