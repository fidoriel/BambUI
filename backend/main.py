from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from .api import router as api_router
import logging
from fastapi.middleware.cors import CORSMiddleware
from .printer_ws import router as ws_router
from fastapi.responses import FileResponse
from .types_general import HealthzResponse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/healthz", response_model=HealthzResponse)
async def healthz() -> HealthzResponse:
    return HealthzResponse(status="healthy")


app.include_router(api_router, prefix="/api")
app.include_router(ws_router, prefix="/ws")

app.mount("", StaticFiles(directory="dist/", html=True, check_dir=True), name="dist")


@app.exception_handler(404)
async def http_exception_handler(request, exc):
    return FileResponse("dist/index.html")
