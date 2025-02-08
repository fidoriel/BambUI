from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from .api import router as api_router
import logging
from fastapi.middleware.cors import CORSMiddleware
from .printer_ws import router as ws_router
from fastapi.responses import FileResponse
from typing import AsyncGenerator
from contextlib import asynccontextmanager
from .printers import printers
from .bot import bot
import asyncio

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("Starting up...")
    for printer in printers.values():
        await printer.start_printer_subscriber()
        logger.info("Started subscribing to %s %s", printer.name, printer.ip)
    task = asyncio.create_task(bot.start_bot_loop())
    yield
    logger.info("Shutting down...")
    task.cancel()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "healthy"}


app.include_router(api_router, prefix="/api")
app.include_router(ws_router, prefix="/ws")

app.mount("", StaticFiles(directory="dist/", html=True, check_dir=True), name="dist")


@app.exception_handler(404)
async def http_exception_handler(request, exc):
    return FileResponse("dist/index.html")
