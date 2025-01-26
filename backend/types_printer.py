from pydantic import BaseModel, field_validator
from typing import Literal, Self, Any, TYPE_CHECKING
import json
from abc import abstractmethod
from . import printer_payload as pl
from .printer_payload import RAW_COMMAND_TYPE
from pydantic import Field
from typing import ClassVar
from base64 import b64decode

if TYPE_CHECKING:
    from .printers import Printer


class PrinterBaseCommand(BaseModel):
    check_idle: ClassVar[bool] = False
    type: Literal[
        "print_speed",
        "bed_temp",
        "extruder_temp",
        "fan_speed",
        "fan_part",
        "fan_aux",
        "fan_chamber",
        "move_x",
        "move_y",
        "move_z",
        "move_e",
        "move_home",
        "stop_print",
        "pause_print",
        "resume_print",
        "force_refresh",
        "load_filament",
        "unload_filament",
        "calibrate",
        "upload_file",
        "chamber_light",
    ]

    async def pre_server_command(self, printer: "Printer") -> None:
        pass

    @abstractmethod
    def to_command(self) -> RAW_COMMAND_TYPE: ...

    async def post_server_command(self, printer: "Printer") -> None:
        pass


class ChamberLight(PrinterBaseCommand):
    type: Literal["chamber_light"] = "chamber_light"
    enable: bool

    def to_command(self) -> RAW_COMMAND_TYPE:
        return pl.enable_light(self.enable)


class Temperature(PrinterBaseCommand):
    temperature: int


class ExtruderTemp(Temperature):
    type: Literal["extruder_temp"] = "extruder_temp"

    def to_command(self) -> RAW_COMMAND_TYPE:
        return pl.extruder_temp_command(self.temperature)


class BedTemp(Temperature):
    type: Literal["bed_temp"] = "bed_temp"

    def to_command(self) -> RAW_COMMAND_TYPE:
        return pl.bed_temp_command(self.temperature)


class PrintSpeed(PrinterBaseCommand):
    type: Literal["print_speed"] = "print_speed"
    speed: Literal[1, 2, 3, 4]

    def to_command(self) -> RAW_COMMAND_TYPE:
        return pl.generate_payload_speed_level(self.speed)


class FanSpeed(PrinterBaseCommand):
    speed: int


class AuxFanSpeed(FanSpeed):
    type: Literal["fan_aux"] = "fan_aux"

    def to_command(self) -> RAW_COMMAND_TYPE:
        return pl.fan_aux_command(self.speed)


class ChamberFanSpeed(FanSpeed):
    type: Literal["fan_chamber"] = "fan_chamber"

    def to_command(self) -> RAW_COMMAND_TYPE:
        return pl.fan_chamber_command(self.speed)


class PartFanSpeed(FanSpeed):
    type: Literal["fan_part"] = "fan_part"

    def to_command(self) -> RAW_COMMAND_TYPE:
        return pl.fan_part_command(self.speed)


class Move(PrinterBaseCommand):
    distance: int

    check_idle: ClassVar[bool] = True


class MoveX(Move):
    type: Literal["move_x"] = "move_x"

    def to_command(self) -> RAW_COMMAND_TYPE:
        return pl.move_x_command(self.distance)


class MoveY(Move):
    type: Literal["move_y"] = "move_y"

    def to_command(self) -> RAW_COMMAND_TYPE:
        return pl.move_y_command(self.distance)


class MoveZ(Move):
    type: Literal["move_z"] = "move_z"

    def to_command(self) -> RAW_COMMAND_TYPE:
        return pl.move_z_command(self.distance)


class MoveE(Move):
    type: Literal["move_e"] = "move_e"

    def to_command(self) -> RAW_COMMAND_TYPE:
        return pl.move_e_command(self.distance)


class MoveHome(PrinterBaseCommand):
    type: Literal["move_home"] = "move_home"

    check_idle: ClassVar[bool] = True

    def to_command(self) -> RAW_COMMAND_TYPE:
        return pl.home_command()


class StopPrint(PrinterBaseCommand):
    type: Literal["stop_print"] = "stop_print"

    def to_command(self) -> RAW_COMMAND_TYPE:
        return pl.stop_command()


class PausePrint(PrinterBaseCommand):
    type: Literal["pause_print"] = "pause_print"

    def to_command(self) -> RAW_COMMAND_TYPE:
        return pl.pause_command()


class ResumePrint(PrinterBaseCommand):
    type: Literal["resume_print"] = "resume_print"

    def to_command(self) -> RAW_COMMAND_TYPE:
        return pl.resume_command()


class FilamentLoad(PrinterBaseCommand):
    type: Literal["load_filament"] = "load_filament"

    check_idle: ClassVar[bool] = True

    def to_command(self) -> RAW_COMMAND_TYPE:
        return pl.filament_load_spool()


class FilamentUnload(PrinterBaseCommand):
    type: Literal["unload_filament"] = "unload_filament"

    check_idle: ClassVar[bool] = True

    def to_command(self) -> RAW_COMMAND_TYPE:
        return pl.filament_unload_spool()


class ForceRefresh(PrinterBaseCommand):
    type: Literal["force_refresh"] = "force_refresh"

    async def pre_server_command(self, printer: "Printer") -> None:
        await printer.force_refresh()

    def to_command(self) -> RAW_COMMAND_TYPE:
        return None


class Calibration(PrinterBaseCommand):
    type: Literal["calibrate"] = "calibrate"
    bed_levelling: bool = True
    motor_noise_cancellation: bool = True
    vibration_compensation: bool = True

    check_idle: ClassVar[bool] = True

    def to_command(self) -> RAW_COMMAND_TYPE:
        return pl.calibration(
            self.bed_levelling,
            self.motor_noise_cancellation,
            self.vibration_compensation,
        )


class PrintFile(PrinterBaseCommand):
    type: Literal["upload_file"] = "upload_file"
    file: bytes
    file_name: str

    check_idle: ClassVar[bool] = True

    @field_validator("file")
    def validate_file(cls, v: bytes) -> bytes:
        try:
            return b64decode(v)
        except (TypeError, ValueError):
            return v

    async def pre_server_command(self, printer: "Printer") -> None:
        await printer.upload_ftps_file(file=self.file, file_path=self.file_name)
        await printer.send_ws_message(f"File '{self.file_name}' uploaded")

    def to_command(self) -> RAW_COMMAND_TYPE:
        return pl.start_print_file(self.file_name)

    async def post_server_command(self, printer: "Printer") -> None:
        await printer.send_ws_message(f"Print '{self.file_name}' started")


class PrinterRequest(BaseModel):
    data: (
        PrintFile
        | Calibration
        | ForceRefresh
        | PrintSpeed
        | BedTemp
        | ExtruderTemp
        | PartFanSpeed
        | ChamberFanSpeed
        | AuxFanSpeed
        | MoveZ
        | MoveZ
        | MoveX
        | MoveE
        | MoveHome
        | StopPrint
        | PausePrint
        | ForceRefresh
        | FilamentLoad
        | FilamentUnload
        | Calibration
        | PrintFile
        | ChamberLight
        | MoveY
        | ResumePrint
    ) = Field(discriminator="type")

    @classmethod
    def from_printer_json(cls, data: dict[Any, Any] | str) -> Self:
        json_data = data
        if isinstance(data, str):
            json_data = json.loads(data)

        return cls.model_validate_json(json.dumps({"data": json_data}))

    def to_command(self) -> RAW_COMMAND_TYPE:
        return self.data.to_command()

    async def pre_server_command(self, printer: "Printer") -> None:
        await self.data.pre_server_command(printer)

    async def post_server_command(self, printer: "Printer") -> None:
        await self.data.post_server_command(printer)
