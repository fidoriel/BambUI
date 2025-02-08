import os
import re
from logging import getLogger
from .asyncCameraClient import AsyncCameraClient
from bambu_connect.utils.models import PrinterStatus
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Callable, Coroutine
from typing import Literal, Any
from pydantic import BaseModel
from uuid import uuid4
from .types_ws import WsJpegImage
from .printer_payload import pushall_command
import ssl
import asyncio
from aiomqtt.client import MqttError, Client as MqttClient
import json
from .types_printer import PrinterRequest
from .types_ws import WsError, WsMessage
from .printer_ftp import PrinterFileSystemEntry, ftps_connection

logger = getLogger(__name__)


class Printer:
    subscribers: dict[str, Callable[[dict[str, Any]], Coroutine[Any, Any, None]]]
    camera_client: AsyncCameraClient | None
    mqtt_client: MqttClient | None
    printer_status: PrinterStatus | None
    printer_status_values: dict[str, Any]
    printer_subscriber_task: asyncio.tasks.Task | None

    name: str
    ip: str
    access_code: str
    serial: str
    model: Literal["P1S", "P1P", "A1", "A1M"]
    username: str = "bblp"
    port: int = 8883
    ftp_port: int = 990

    full_push: bool = False
    latest_image: bytes | None = None

    def __init__(
        self, name: str, ip: str, access_code: str, serial: str, model: Literal["P1S"]
    ):
        self.name = name
        self.ip = ip
        self.serial = serial
        self.model = model
        self.access_code = access_code

        self.subscribers = {}
        self.camera_client = None
        self.mqtt_client = None
        self.printer_status = None
        self.printer_status_values = {}
        self.printer_subscriber_task = None

    @property
    def request_topic(self) -> str:
        return f"device/{self.serial}/request"

    @property
    def is_idle_print(self) -> str:
        return self.printer_status_values.get("print_type", "").lower() == "idle"

    async def image_callback(self, image: bytes) -> None:
        self.latest_image = image
        await self.callback_all_connected_ws(WsJpegImage.from_bytes(image))

    async def start_printer_subscriber(self):
        if self.printer_subscriber_task is None or self.printer_subscriber_task.done():
            self.printer_subscriber_task = asyncio.create_task(
                self.printer_subscriber()
            )
            logger.info("Created new task for %s", self.name)

            def on_done(task: asyncio.tasks.Task):
                self.full_push = False
                try:
                    task.result()
                except asyncio.CancelledError:
                    logger.info("Printer subscriber cancelled for %s", self.name)
                except Exception as e:
                    logger.exception(
                        "Printer subscriber failed for %s: %s", self.name, e
                    )
                self.printer_subscriber_task = None
                if self.subscribers:
                    self.printer_subscriber_task = asyncio.create_task(
                        self.start_printer_subscriber()
                    )

            self.printer_subscriber_task.add_done_callback(on_done)

    async def start(
        self, callback: Callable[[dict[str, Any]], Coroutine[Any, Any, None]]
    ) -> None:
        if not self.subscribers:
            logger.error("Started Printer Connection without subscribers")
            return

        if self.camera_client is None:
            self.camera_client = AsyncCameraClient(
                hostname=self.ip, access_code=self.access_code
            )
        if self.camera_client is not None:
            await self.camera_client.start_stream(self.image_callback)

        if self.mqtt_client is None:
            ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS)
            ssl_context.verify_mode = ssl.CERT_NONE
            ssl_context.check_hostname = False
            self.mqtt_client = MqttClient(
                hostname=self.ip,
                username=self.username,
                password=self.access_code,
                port=self.port,
                tls_insecure=True,
                tls_context=ssl_context,
            )
            await self.start_printer_subscriber()

    async def stop(self, force: bool = False) -> None:
        if self.subscribers and not force:
            logger.info(
                "Not stopping %s %s because printer has connected users",
                self.name,
                self.model,
            )
            return

        if force:
            logger.info(
                "Force stopping %s %s despite %d connected users",
                self.name,
                self.model,
                len(self.subscribers),
            )

        if self.camera_client is not None:
            await self.camera_client.stop_stream()
            self.camera_client = None

        logger.info("Tasks for %s stopped", self.name)

    async def callback_all_connected_ws(
        self, payload: dict[str, Any] | BaseModel
    ) -> None:
        payload_dict = (
            payload.model_dump() if isinstance(payload, BaseModel) else payload
        )

        for callback in self.subscribers.values():
            await callback(payload_dict)

    async def send_ws_error(self, message: str) -> None:
        await self.callback_all_connected_ws(WsError(message=message))

    async def send_ws_message(self, message: str) -> None:
        await self.callback_all_connected_ws(WsMessage(message=message))

    async def publish_request(self, payload: str | dict[str, Any]) -> None:
        if isinstance(payload, dict):
            payload = json.dumps(payload)

        if self.mqtt_client is not None:
            try:
                logger.info("Publishing %s to %s %s", payload, self.name, self.model)
                await self.mqtt_client.publish(self.request_topic, payload)
            except MqttError:
                await self.send_ws_error("Printer MQTT Connection Error")
                logger.error("Cannot send request because MQTT connection faulty")
        else:
            logger.error("Cannot send request because client not connected")

    async def request_full_push(self) -> None:
        if not self.full_push:
            await self.publish_request(json.dumps(pushall_command()))
            logger.info("Requested full push from %s %s", self.name, self.model)

    async def printer_subscriber(self) -> None:
        while True:
            if self.mqtt_client is None:
                await asyncio.sleep(0.1)
                continue
            try:
                async with self.mqtt_client as client:
                    await self.request_full_push()
                    await client.subscribe(f"device/{self.serial}/report")
                    async for message in client.messages:
                        try:
                            if not isinstance(message.payload, bytes):
                                logger.error(
                                    "Printer %s %s sent unexpected %s",
                                    self.name,
                                    self.model,
                                    message.payload,
                                )
                                continue
                            payload = json.loads(message.payload)
                            logger.info(
                                "Received from %s %s %s", self.name, self.model, payload
                            )

                            if self.printer_status_values is None:
                                self.printer_status_values = {}

                            if print_payload := payload.get("print"):
                                self.printer_status_values.update(print_payload)
                                if print_payload.get("msg") == 0:
                                    self.full_push = True

                            elif system_payload := payload.get("print"):
                                if led_status := system_payload.get("led_mode"):
                                    if (
                                        len(self.printer_status_values["lights_report"])
                                        == 1
                                    ):
                                        self.printer_status_values["lights_report"][
                                            "mode"
                                        ] = led_status

                            client_payload = {
                                "type": "printer_status",
                                "data": self.printer_status_values,
                            }
                            if self.full_push:
                                await self.callback_all_connected_ws(client_payload)
                            await self.request_full_push()

                        except KeyError:
                            logger.error(
                                "Error while subscribing %s %s", self.name, self.model
                            )
                            continue
            except MqttError:
                await asyncio.sleep(3)

    @asynccontextmanager
    async def client(
        self, callback: Callable[[dict[str, Any]], Coroutine[Any, Any, None]]
    ) -> AsyncGenerator[None, None]:
        uuid = str(uuid4())
        self.subscribers[uuid] = callback
        await self.start(callback)
        try:
            yield None
        finally:
            del self.subscribers[uuid]
            await self.stop()

    async def force_refresh(self) -> None:
        logger.info("force restarting %s", self.name)
        await self.stop(force=True)
        for callback in self.subscribers.values():
            await self.start(callback)

    async def hanlde_request(self, request: PrinterRequest) -> None:
        if request.data.check_idle and not self.is_idle_print:
            logger.info("Printer is not Idle")
            await self.send_ws_error("Printer not Idle")
            return
        await request.pre_server_command(self)
        if command := request.to_command():
            await self.publish_request(command)
        await request.post_server_command(self)

    async def list_ftps_files(self) -> list[PrinterFileSystemEntry]:
        files = []
        async with ftps_connection(
            host=self.ip,
            port=self.ftp_port,
            user=self.username,
            password=self.access_code,
        ) as client:
            raw_files = await client.list(recursive=False)
            for path, meta in raw_files:
                files.append(
                    PrinterFileSystemEntry(
                        path=path,
                        entry_type=meta["type"],
                        size=meta["size"],
                        modify=meta["modify"],
                    )
                )
        return files

    async def upload_ftps_file(self, file: bytes, file_path: str) -> None:
        async with ftps_connection(
            host=self.ip,
            port=self.ftp_port,
            user=self.username,
            password=self.access_code,
        ) as client:
            stream = await client.upload_stream(destination=file_path)
            await stream.write(file)
            stream.close()
        return None

    async def delete_ftps_file(self, file: bytes, file_path: str) -> None:
        async with ftps_connection(
            host=self.ip,
            port=self.ftp_port,
            user=self.username,
            password=self.access_code,
        ) as client:
            client.remove(path=file_path)
        return None


def parse_printers_from_env() -> dict[str, Printer]:
    printers_read: dict[str, dict[str, Any]] = {}
    for key, value in os.environ.items():
        match = re.match(r"BAMBUI_PRINTER\.([^.]+)\.(IP|ACCESS_CODE|SERIAL|MODEL)", key)
        if match:
            name, attribute = match.groups()
            if name not in printers_read:
                printers_read[name] = {}
            printers_read[name][attribute.lower()] = value

    _printers = {
        name: Printer(name=name, **details) for name, details in printers_read.items()
    }
    logger.info("Printers: %s", ",".join(_printers.keys()))
    return _printers


printers = parse_printers_from_env()
