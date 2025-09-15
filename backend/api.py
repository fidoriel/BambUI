from fastapi import APIRouter
from .printers import printers
from .printers import Printer
import asyncio
from .types_general import PrinterResponse
from fastapi import HTTPException

router = APIRouter()


@router.get("/printers")
async def get_printers() -> list[PrinterResponse]:
    async def get_printer_status(printer: Printer) -> PrinterResponse:
        return PrinterResponse(
            name=printer.name,
            model=printer.model,
            is_online=await printer.ping(),
            supports_chamber_temp=printer.supports_chamber_temp,
        )

    return await asyncio.gather(
        *[get_printer_status(printer) for printer in printers.values()]
    )


@router.get("/printer/{name}")
async def get_printer(name: str) -> PrinterResponse:
    printer = next((p for p in printers.values() if p.name == name), None)
    if not printer:
        raise HTTPException(status_code=404, detail="Printer not found")
    return PrinterResponse(
        name=printer.name,
        model=printer.model,
        is_online=await printer.ping(),
        supports_chamber_temp=printer.supports_chamber_temp,
    )
