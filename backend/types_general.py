from pydantic import BaseModel
from typing import Literal
from enum import Enum


BBL_P1S = "P1S"
BBL_P1P = "P1P"
BBL_A1 = "A1"
BBL_A1M = "A1M"
BBL_X1 = "X1"
BBL_X1C = "X1C"
BBL_X1E = "X1E"
BBL_H2D = "H2D"
BBL_H2S = "H2S"


class SupportedPrinters(str, Enum):
    P1S = BBL_P1S
    P1P = BBL_P1P
    A1M = BBL_A1M
    A1 = BBL_A1


class HealthzResponse(BaseModel):
    status: Literal["healthy"]


class ErrorResponse(BaseModel):
    error: str


class PrinterResponse(BaseModel):
    name: str
    model: SupportedPrinters
    is_online: bool
    supports_chamber_temp: bool
