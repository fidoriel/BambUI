import logging
import os
from aiogram import Bot, Dispatcher, html
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.types import Message

logger = logging.getLogger(__name__)

bot_token = os.environ.get("TELEGRAM_TOKEN")
allowed_users = os.environ.get("TELEGRAM_ALLOWED_USERS", "")


class TelegramBot:
    bot: Bot | None = None
    dispatcher: Dispatcher | None = None
    allowed_chats: list[str]

    def __init__(self):
        logger.info("Subscribed Users %s", allowed_users)
        if bot_token is None or allowed_users is None:
            logger.error("Telegram Bot token or allowed users not configured")
            return

        self.bot = Bot(
            token=bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML)
        )
        self.dispatcher = Dispatcher()
        self.allowed_chats = allowed_users.split(",")

        self.dispatcher.message.register(self.command_start, CommandStart())
        self.dispatcher.message.register(
            self.command_printer_information, Command("info")
        )
        self.dispatcher.message.register(self.command_help, Command("help"))

    async def command_start(self, message: Message) -> None:
        from .printers import printers

        if str(message.chat.id) not in self.allowed_chats:
            logger.warning("Chat %s not allowed", message.chat.id)

        printer_list = "\n".join(
            [f"{i+1}. {name}" for i, name in enumerate(printers.keys())]
        )
        await message.answer(
            f"I'm the BambUI bot. Currently connected printers are \n{html.bold(printer_list)}"
        )

    async def command_printer_information(self, message: Message) -> None:
        from .printers import printers

        if str(message.chat.id) not in self.allowed_chats:
            logger.warning("Chat %s not allowed", message.chat.id)

        printer_list = "\n".join(
            [f"{i+1}. {printer.ip}" for i, printer in enumerate(printers.values())]
        )
        await message.answer(
            f"I'm the BambUI bot. Currently connected printers are \n{html.bold(printer_list)}"
        )

    async def command_help(self, message: Message) -> None:
        await message.answer(
            f"""
/help - see this
/start - introduction
/info - information about your printers

You may want to register the commands within botfather:

{html.code(
'''
help - get help and bot setup information
start - introduction to BambUI Telegram Bot
info - information about your printers
'''
)}
"""
        )

    async def send(self, message: str) -> None:
        if self.bot is None:
            logger.warning("Telegram Bot not initialized")
            return

        for chat in self.allowed_chats:
            try:
                await self.bot.send_message(chat_id=int(chat), text=message)
            except Exception as e:
                logger.exception("Failed to send to User %s", chat, exc_info=e)

    async def start_bot_loop(self):
        if self.bot is None or self.dispatcher is None:
            logger.error("Bot or Dispatcher not initialized")
            return

        await self.dispatcher.start_polling(
            self.bot, handle_signals=False, handle_as_tasks=True
        )


bot = TelegramBot()
