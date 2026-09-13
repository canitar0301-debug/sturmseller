import logging
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, ParseMode
from telegram.error import TelegramError

logger = logging.getLogger(__name__)


class TelegramBot:

  def __init__(self, token, chat_ids):
    self.bot = Bot(token)
    # Поддерживает как список, так и одиночную строку/число
    if isinstance(chat_ids, (str, int)):
      self.chat_ids = [chat_ids]
    else:
      self.chat_ids = chat_ids or []

  def send_message(
      self,
      text,
      parse_mode=ParseMode.HTML,
      image_url=None,
      product_url=None,
  ):
    keyboard = []
    if product_url:
      keyboard = [
          [InlineKeyboardButton("🔗 Перейти к товару", url=product_url)]
      ]

    reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None

    # Рассылка по всем указанным чатам/каналам
    for chat_id in self.chat_ids:
      try:
        if image_url:
          self.bot.send_photo(
              chat_id=chat_id,
              photo=image_url,
              caption=text,
              parse_mode=parse_mode,
              reply_markup=reply_markup,
          )
        else:
          self.bot.send_message(
              chat_id=chat_id,
              text=text,
              parse_mode=parse_mode,
              reply_markup=reply_markup,
          )
      except TelegramError as e:
        logger.error(
            f"Ошибка отправки сообщения в чат/канал {chat_id}: {str(e)}"
        )
