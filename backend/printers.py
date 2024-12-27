import os
import re
from logging import getLogger
from bambu_connect.CameraClient import CameraClient
from bambu_connect.utils.models import PrinterStatus
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Callable, Coroutine
from typing import Literal, Any
from uuid import uuid4
import base64

import ssl
import asyncio
from aiomqtt.client import MqttError, Client as MqttClient
import json

logger = getLogger()


class Printer:
    subscribers: dict[str, Callable[[dict[str, Any]], Coroutine[Any, Any, None]]]
    camera_client: CameraClient | None
    mqtt_client: MqttClient | None
    printer_status: PrinterStatus | None
    printer_status_values: dict[str, Any]
    printer_subscriber_task: asyncio.tasks.Task | None

    name: str
    ip: str
    access_code: str
    serial: str
    model: Literal["P1S"]
    username: str = "bblp"
    port: int = 8883

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

    def get_image_payload(self, image: bytes) -> dict[str, Any]:
        return {
            "type": "jpeg_image",
            "data": base64.b64encode(image).decode("utf-8"),
        }

    def image_callback(self, image: bytes) -> None:
        self.latest_image = image
        payload = self.get_image_payload(image)

        for callback in self.subscribers.values():
            asyncio.run(callback(payload))

    async def start_printer_subscriber(self):
        if self.printer_subscriber_task is None or self.printer_subscriber_task.done():
            self.printer_subscriber_task = asyncio.create_task(
                self.printer_subscriber()
            )
            logger.info("Created new task for %s", self.name)

            def on_done(task):
                self.full_push = False
                try:
                    task.result()
                except asyncio.CancelledError:
                    logger.info("Printer subscriber cancelled for %s", self.name)
                except Exception as e:
                    logger.exception(
                        "Printer subscriber failed for %s: %s", self.name, e
                    )

            self.printer_subscriber_task.add_done_callback(on_done)

    async def start(
        self, callback: Callable[[dict[str, Any]], Coroutine[Any, Any, None]]
    ) -> None:
        if not self.subscribers:
            logger.error("Started Printer Connection without subscribers")
            return

        if self.camera_client is None:
            self.camera_client = CameraClient(
                hostname=self.ip, access_code=self.access_code
            )
        if self.camera_client is not None:
            if self.latest_image:
                await callback(self.get_image_payload(self.latest_image))
            self.camera_client.start_stream(self.image_callback)

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

    async def stop(self) -> None:
        if self.subscribers:
            return

        if self.camera_client is not None:
            self.camera_client.stop_stream()
            self.camera_client = None

        logger.info("Tasks for %s stopped", self.name)

    async def request_full_push(self) -> None:
        if not self.full_push and self.mqtt_client is not None:
            await self.mqtt_client.publish(
                self.request_topic,
                '{"pushing": { "sequence_id": 0, "command": "pushall"}, "user_id":"1234567890"}',
            )
            logger.info("Requested full push")

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
                                "data": json.dumps(self.printer_status_values),
                            }
                            for callback in self.subscribers.values():
                                await callback(client_payload)
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

    async def set_light(self, status: bool) -> None:
        mode = "on" if status else "off"
        if self.mqtt_client:
            await self.mqtt_client.publish(
                self.request_topic, json.dumps({"system": {"led_mode": mode}})
            )
        else:
            raise ConnectionError("Printer not connected")


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
