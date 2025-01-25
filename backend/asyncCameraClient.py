import ssl
from logging import getLogger

import asyncio
from bambu_connect.CameraClient import CameraClient


import logging

logger = getLogger(__name__)

logger = logging.getLogger(__name__)


class AsyncCameraClient(CameraClient):
    async def capture_stream(self, img_callback):
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        jpeg_start = bytearray([0xFF, 0xD8, 0xFF, 0xE0])
        jpeg_end = bytearray([0xFF, 0xD9])
        read_chunk_size = 4096

        while self.streaming:
            try:
                reader, writer = await asyncio.open_connection(
                    host=self.hostname, port=self.port, ssl=ctx
                )

                logger.info("Connected to server")

                writer.write(self.auth_packet)
                await writer.drain()

                buf = bytearray()

                while self.streaming:
                    try:
                        data = await asyncio.wait_for(
                            reader.read(read_chunk_size), timeout=5
                        )
                        if not data:
                            break

                        buf += data
                        img, buf = self.__find_jpeg__(buf, jpeg_start, jpeg_end)
                        if img:
                            await img_callback(bytes(img))

                    except Exception as e:
                        logger.error("Error reading stream: %s", e)
                        break

                writer.close()
                await writer.wait_closed()

            except Exception as e:
                logger.error(f"Connection error: {e}")
                await asyncio.sleep(1)
                break

    async def start_stream(self, img_callback):
        if self.streaming:
            logger.info("Stream for %s already running.", self.hostname)
            return

        self.streaming = True

        def on_done(task: asyncio.tasks.Task):
            try:
                task.result()
            except Exception as e:
                logger.error(f"Stream task encountered an error: {e}")
            finally:
                self.streaming = False

        try:
            self.stream_task = asyncio.create_task(self.capture_stream(img_callback))
            self.stream_task.add_done_callback(on_done)
        except Exception as e:
            logger.error(f"An error occurred while starting the stream: {e}")
            self.streaming = False

    async def stop_stream(self):
        if not self.streaming:
            logger.warning("Stream for %s is not running.", self.hostname)
            return

        self.streaming = False
        if self.stream_task:
            await self.stream_task
