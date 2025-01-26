from typing import Literal

RAW_COMMAND_TYPE = (
    dict[
        str,
        dict[str, str | int | list[str] | list[int] | None]
        | int
        | str
        | list[str]
        | list[int]
        | None,
    ]
    | None
)

FAN_NUM_PART = 1
FAN_NUM_AUX = 2
FAN_NUM_CHAMBER = 3


def enable_light(status: bool) -> RAW_COMMAND_TYPE:
    mode = "on" if status else "off"
    return {"system": {"led_mode": mode}}


def generate_gcode_payload(
    gcode_line: str,
) -> RAW_COMMAND_TYPE:
    return {"print": {"command": "gcode_line", "param": f"{gcode_line}"}}


def generate_payload_speed_level(
    speed_level: Literal[1, 2, 3, 4],
) -> RAW_COMMAND_TYPE:
    return {"print": {"command": "print_speed", "param": f"{speed_level}"}}


def bed_temp_command(temperature: int) -> RAW_COMMAND_TYPE:
    return generate_gcode_payload(f"M140 S{temperature}\n")


def extruder_temp_command(
    temperature: int,
) -> RAW_COMMAND_TYPE:
    return generate_gcode_payload(f"M104 S{temperature}\n")


def fan_speed_gcode(speed: int, fan_num: int) -> RAW_COMMAND_TYPE:
    return generate_gcode_payload(f"M106 P{fan_num} S{speed}\n")


def fan_aux_command(speed: int) -> RAW_COMMAND_TYPE:
    return fan_speed_gcode(speed, FAN_NUM_AUX)


def fan_chamber_command(speed: int) -> RAW_COMMAND_TYPE:
    return fan_speed_gcode(speed, FAN_NUM_CHAMBER)


def fan_part_command(speed: int) -> RAW_COMMAND_TYPE:
    return fan_speed_gcode(speed, FAN_NUM_PART)


def move_x_command(mm: int) -> RAW_COMMAND_TYPE:
    return generate_gcode_payload(f"G91\nG0 X{mm}\nG90\n")


def move_y_command(mm: int) -> RAW_COMMAND_TYPE:
    return generate_gcode_payload(f"G91\nG0 Y{mm}\nG90\n")


def move_z_command(mm: int) -> RAW_COMMAND_TYPE:
    return generate_gcode_payload(f"G91\nG0 Z{mm}\nG90\n")


def move_e_command(mm: int) -> RAW_COMMAND_TYPE:
    return generate_gcode_payload(f"G91\nG0 E{mm}\nG90\n")


def home_command() -> RAW_COMMAND_TYPE:
    return generate_gcode_payload("G28\n")


def stop_command() -> RAW_COMMAND_TYPE:
    return {"print": {"command": "stop"}}


def pause_command() -> RAW_COMMAND_TYPE:
    return {"print": {"command": "pause"}}


def resume_command() -> RAW_COMMAND_TYPE:
    return {"print": {"command": "resume"}}


def pushall_command() -> RAW_COMMAND_TYPE:
    return {
        "pushing": {"sequence_id": 0, "command": "pushall"},
        "user_id": "1234567890",
    }


def filament_load_spool() -> RAW_COMMAND_TYPE:
    return {
        "print": {
            "command": "ams_change_filament",
            "target": 255,
            "curr_temp": 215,
            "tar_temp": 215,
        }
    }


def filament_unload_spool() -> RAW_COMMAND_TYPE:
    return {
        "print": {
            "command": "ams_change_filament",
            "target": 254,
            "curr_temp": 215,
            "tar_temp": 215,
        }
    }


def resume_filament_action() -> RAW_COMMAND_TYPE:
    return {
        "print": {
            "command": "ams_control",
            "param": "resume",
        }
    }


def calibration(
    bed_levelling: bool = True,
    motor_noise_cancellation: bool = True,
    vibration_compensation: bool = True,
) -> RAW_COMMAND_TYPE:
    bitmask = 0

    if bed_levelling:
        bitmask |= 1 << 1
    if vibration_compensation:
        bitmask |= 1 << 2
    if motor_noise_cancellation:
        bitmask |= 1 << 3

    return {"print": {"command": "calibration", "option": bitmask}}


def start_print_file(
    filename: str,
) -> RAW_COMMAND_TYPE:
    return {
        "print": {
            "command": "project_file",
            "param": "Metadata/plate_1.gcode",
            "subtask_name": f"{filename}",
            "url": f"ftp://{filename}",
            "bed_type": "auto",
            "timelapse": False,
            "bed_leveling": True,
            "flow_cali": False,
            "vibration_cali": True,
            "layer_inspect": False,
            "use_ams": False,
            "profile_id": "0",
            "project_id": "0",
            "subtask_id": "0",
            "task_id": "0",
        }
    }
