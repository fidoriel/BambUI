from pydantic import BaseModel
from typing import Literal
import base64


class WsBaseCommand(BaseModel):
    type: Literal["error", "jpeg_image", "printer_status", "message"]


class WsError(WsBaseCommand):
    type: Literal["error"] = "error"
    message: str


class WsMessage(WsBaseCommand):
    type: Literal["message"] = "message"
    message: str


class WsJpegImage(WsBaseCommand):
    type: Literal["jpeg_image"] = "jpeg_image"
    image: str  # base64

    @classmethod
    def from_bytes(cls, image: bytes) -> "WsJpegImage":
        return WsJpegImage(image=base64.b64encode(image).decode("utf-8"))
