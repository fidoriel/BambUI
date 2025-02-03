from telegram import Bot
import os
from logging import getLogger

logger = getLogger(__name__)

bot_token = os.environ.get("TELEGRAM_TOKEN")
allowed_users = os.environ.get("TELEGRAM_ALLOWED_USERS", "")


class TelegramBot:
    bot: Bot | None = None
    allowed_chats: list[str]

    def __init__(self):
        logger.info("Subscribed Users %s", allowed_users)
        if bot_token is None or allowed_users is None:
            return

        self.bot = Bot(bot_token)
        self.allowed_chats = allowed_users.split(",")

    async def send(self, mesasge: str) -> None:
        if self.bot is None:
            logger.warning("Telegram Bot not initialized")
            return

        for chat in self.allowed_chats:
            logger.error(chat)
            try:
                await self.bot.send_message(chat_id=int(chat), text=mesasge)
            except Exception as e:
                logger.exception("Failed to send to User %s", chat, exc_info=e)


bot = TelegramBot()
