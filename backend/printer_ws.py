from fastapi import WebSocket, APIRouter
from starlette.websockets import WebSocketState, WebSocketDisconnect
from .printers import printers
from logging import getLogger
from typing import Any

logger = getLogger(__name__)

router = APIRouter()


@router.websocket("/printer/{printer_id}")
async def printer_websocket(websocket: WebSocket, printer_id: str):
    printer = printers.get(printer_id)
    if printer is None:
        await websocket.close(code=4004, reason="Invalid Printer Name")
        return

    await websocket.accept()

    async def socket_callback(data: dict[str, Any]) -> None:
        if websocket.client_state == WebSocketState.CONNECTED:
            await websocket.send_json(data)

    async with printer.client(socket_callback):
        try:
            while True:
                data = await websocket.receive_json()
                logger.info(
                    "Received from user for %s %s %s", printer.name, printer.model, data
                )

                if data.get("type") == "chamber_light":
                    await printer.set_light(data.get("data"))
                elif data.get("type") == "force_refresh":
                    await printer.force_refresh()

        except WebSocketDisconnect:
            pass
        except Exception as e:
            logger.exception("Error with printer %s", printer_id, e)
