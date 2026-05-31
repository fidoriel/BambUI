import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, html
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.filters.callback_data import CallbackData
from aiogram.types import Message, BufferedInputFile, CallbackQuery, BotCommand
from aiogram.utils.keyboard import InlineKeyboardBuilder
import webcolors

logger = logging.getLogger(__name__)

bot_token = os.environ.get("TELEGRAM_API_KEY")


class ImageCallback(CallbackData, prefix="image"):
    printer_name: str


allowed_users = os.environ.get("TELEGRAM_ALLOWED_USERS", "")


def _hex_to_color_name(hex_color: str) -> str:
    """Convert a hex color string (RRGGBB or RRGGBBAA) to the closest CSS3 color name."""
    hex_color = hex_color.lstrip("#")
    if len(hex_color) < 6:
        return hex_color
    try:
        r, g, b = (
            int(hex_color[0:2], 16),
            int(hex_color[2:4], 16),
            int(hex_color[4:6], 16),
        )
    except ValueError:
        return hex_color

    try:
        return webcolors.rgb_to_name((r, g, b))
    except ValueError:
        pass

    best_name = hex_color
    best_dist = float("inf")
    for name in webcolors.names():
        cr, cg, cb = webcolors.name_to_rgb(name)
        dist = (r - cr) ** 2 + (g - cg) ** 2 + (b - cb) ** 2
        if dist < best_dist:
            best_dist = dist
            best_name = name
    return best_name


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

        self.dispatcher.message.register(self.command_help, Command("help"))
        self.dispatcher.message.register(self.command_image, Command("image"))
        self.dispatcher.callback_query.register(
            self.callback_image, ImageCallback.filter()
        )
        self.dispatcher.message.register(self.command_status, Command("status"))

    async def _send_printer_image(self, printer_name: str, chat_id: int) -> None:
        """Capture and send the current camera image for a printer.

        Turns the light on if needed, waits for a fresh frame, sends the
        photo, then restores the light to its previous state.
        """
        from .printers import printers
        from .printer_payload import enable_light

        printer = printers.get(printer_name)
        if printer is None:
            if self.bot:
                await self.bot.send_message(
                    chat_id=chat_id,
                    text=f"{html.bold(printer_name)}: Printer is not connected.",
                )
            return

        # Turn the light on if it is off so the image is useful
        lights = printer.printer_status_values.get("lights_report", [])
        light_was_off = (
            isinstance(lights, list)
            and len(lights) > 0
            and lights[0].get("mode") != "on"
        )
        if light_was_off:
            if cmd := enable_light(True):
                await printer.publish_request(cmd)
            await asyncio.sleep(0.5)

        image = await printer.capture_fresh_image()
        if self.bot and image is not None:
            photo = BufferedInputFile(file=image, filename=f"{printer_name}.jpg")
            await self.bot.send_photo(
                chat_id=chat_id, photo=photo, caption=printer_name
            )
        elif self.bot:
            await self.bot.send_message(
                chat_id=chat_id,
                text=f"{html.bold(printer_name)}: No image available.",
            )

        # Restore the light to its previous state
        if light_was_off:
            if cmd := enable_light(False):
                await printer.publish_request(cmd)

    async def command_image(self, message: Message) -> None:
        from .printers import printers

        if str(message.chat.id) not in self.allowed_chats:
            logger.warning("Chat %s not allowed", message.chat.id)
            return

        if not printers:
            await message.answer("No printers configured.")
            return

        if len(printers) == 1:
            name = next(iter(printers))
            await self._send_printer_image(name, message.chat.id)
            return

        builder = InlineKeyboardBuilder()
        for name in printers:
            builder.button(
                text=name,
                callback_data=ImageCallback(printer_name=name),
            )
        builder.adjust(1)
        await message.answer("Select a printer:", reply_markup=builder.as_markup())

    async def callback_image(
        self, callback: CallbackQuery, callback_data: ImageCallback
    ) -> None:
        if not isinstance(callback.message, Message):
            await callback.answer("Invalid callback.")
            return

        if str(callback.message.chat.id) not in self.allowed_chats:
            logger.warning("Chat %s not allowed", callback.message.chat.id)
            await callback.answer("Not allowed.")
            return

        await callback.answer()
        await self._send_printer_image(
            callback_data.printer_name, callback.message.chat.id
        )

    async def command_status(self, message: Message) -> None:
        from .printers import printers

        if str(message.chat.id) not in self.allowed_chats:
            logger.warning("Chat %s not allowed", message.chat.id)
            return

        if not printers:
            await message.answer("No printers configured.")
            return

        for name, printer in printers.items():
            status = printer.printer_status_values
            if not status:
                await message.answer(f"{html.bold(name)}: No status available yet.")
                continue

            gcode_state = status.get("gcode_state", "Unknown")
            percent = status.get("mc_percent", 0)
            remaining = status.get("mc_remaining_time", 0)
            subtask = status.get("subtask_name", "")
            nozzle_temp = status.get("nozzle_temper", 0)
            nozzle_target = status.get("nozzle_target_temper", 0)
            bed_temp = status.get("bed_temper", 0)
            bed_target = status.get("bed_target_temper", 0)
            layer = status.get("layer_num", 0)
            total_layers = status.get("total_layer_num", 0)

            hours, minutes = divmod(remaining, 60)

            lines = [
                f"{html.bold(name)} ({printer.ip})",
                f"State: {gcode_state}",
            ]

            if subtask:
                lines.append(f"File: {subtask}")

            if gcode_state not in ("IDLE", "FAILED", "FINISH"):
                lines.append(f"Progress: {percent}%")
                lines.append(f"Remaining: {hours}h {minutes}m")
                lines.append(f"Layer: {layer}/{total_layers}")

            lines.append(f"Nozzle: {nozzle_temp:.0f}/{nozzle_target:.0f} C")
            lines.append(f"Bed: {bed_temp:.0f}/{bed_target:.0f} C")

            ams_data = status.get("ams")
            if isinstance(ams_data, dict):
                ams_units = ams_data.get("ams", [])
                if isinstance(ams_units, list) and ams_units:
                    lines.append("")
                    lines.append(html.bold("AMS"))
                    for unit in ams_units:
                        trays = unit.get("tray", [])
                        if not isinstance(trays, list):
                            continue
                        humidity = unit.get("humidity", "?")
                        lines.append(
                            f"Unit {unit.get('id', '?')} (Humidity: {humidity}%)"
                        )
                        for tray in trays:
                            slot = tray.get("id", "?")
                            filament = tray.get("tray_type", "")
                            color = tray.get("tray_color", "")
                            remaining = tray.get("remain", -1)
                            if filament:
                                parts = [f"  Slot {slot}: {filament}"]
                                if color:
                                    parts.append(f"({_hex_to_color_name(color)})")
                                if remaining >= 0:
                                    parts.append(f"{remaining}%")
                                lines.append(" ".join(parts))
                            else:
                                lines.append(f"  Slot {slot}: Empty")

            await message.answer("\n".join(lines))

    async def command_help(self, message: Message) -> None:
        await message.answer(
            """
/help - see this
/status - printer status and progress
/image - current camera snapshot
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

    async def send_photo(self, image: bytes, caption: str) -> None:
        if self.bot is None:
            logger.warning("Telegram Bot not initialized")
            return

        photo = BufferedInputFile(file=image, filename="print.jpg")
        for chat in self.allowed_chats:
            try:
                await self.bot.send_photo(
                    chat_id=int(chat), photo=photo, caption=caption
                )
            except Exception as e:
                logger.exception("Failed to send photo to User %s", chat, exc_info=e)

    async def start_bot_loop(self):
        if self.bot is None or self.dispatcher is None:
            logger.error("Bot or Dispatcher not initialized")
            return

        await self.bot.set_my_commands(
            [
                BotCommand(
                    command="help", description="Get help and bot setup information"
                ),
                BotCommand(command="status", description="Printer status and progress"),
                BotCommand(command="image", description="Current camera snapshot"),
            ]
        )

        await self.dispatcher.start_polling(
            self.bot, handle_signals=False, handle_as_tasks=True
        )


bot = TelegramBot()
