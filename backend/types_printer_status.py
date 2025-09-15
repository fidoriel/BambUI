from typing import Any
from pydantic import BaseModel


class Upload(BaseModel):
    status: str | None = None
    progress: int | None = None
    message: str | None = None


class Online(BaseModel):
    ahb: bool | None = None
    rfid: bool | None = None
    version: int | None = None


class VTTray(BaseModel):
    id: str | None = None
    tag_uid: str | None = None
    tray_id_name: str | None = None
    tray_info_idx: str | None = None
    tray_type: str | None = None
    tray_sub_brands: str | None = None
    tray_color: str | None = None
    tray_weight: str | None = None
    tray_diameter: str | None = None
    tray_temp: str | None = None
    tray_time: str | None = None
    bed_temp_type: str | None = None
    bed_temp: str | None = None
    nozzle_temp_max: str | None = None
    nozzle_temp_min: str | None = None
    xcam_info: str | None = None
    tray_uuid: str | None = None
    remain: int | None = None
    k: float | None = None
    n: int | None = None
    cali_idx: int | None = None


class AMSEntry(BaseModel):
    humidity: str | None = None
    id: str | None = None
    temp: str | None = None
    tray: list[VTTray] | None = None


class AMS(BaseModel):
    ams: list[AMSEntry] | None = None
    ams_exist_bits: str | None = None
    tray_exist_bits: str | None = None
    tray_is_bbl_bits: str | None = None
    tray_tar: str | None = None
    tray_now: str | None = None
    tray_pre: str | None = None
    tray_read_done_bits: str | None = None
    tray_reading_bits: str | None = None
    version: int | None = None
    insert_flag: bool | None = None
    power_on_flag: bool | None = None


class IPCam(BaseModel):
    ipcam_dev: str | None = None
    ipcam_record: str | None = None
    timelapse: str | None = None
    resolution: str | None = None
    tutk_server: str | None = None
    mode_bits: int | None = None


class LightsReport(BaseModel):
    node: str | None = None
    mode: str | None = None


class UpgradeState(BaseModel):
    sequence_id: int | None = None
    progress: str | None = None
    status: str | None = None
    consistency_request: bool | None = None
    dis_state: int | None = None
    err_code: int | None = None
    force_upgrade: bool | None = None
    message: str | None = None
    module: str | None = None
    new_version_state: int | None = None
    new_ver_list: list[Any] | None = None
    cur_state_code: int | None = None
    idx2: int | None = None


class PrinterStatus(BaseModel):
    upload: Upload | None = None
    nozzle_temper: float | None = None
    nozzle_target_temper: float | None = None
    bed_temper: float | None = None
    bed_target_temper: float | None = None
    chamber_temper: float | None = None
    mc_print_stage: str | None = None
    heatbreak_fan_speed: str | None = None
    cooling_fan_speed: str | None = None
    big_fan1_speed: str | None = None
    big_fan2_speed: str | None = None
    mc_percent: int | None = None
    mc_remaining_time: int | None = None
    ams_status: int | None = None
    ams_rfid_status: int | None = None
    hw_switch_state: int | None = None
    spd_mag: int | None = None
    spd_lvl: int | None = None
    print_error: int | None = None
    lifecycle: str | None = None
    wifi_signal: str | None = None
    gcode_state: str | None = None
    gcode_file_prepare_percent: str | None = None
    queue_number: int | None = None
    queue_total: int | None = None
    queue_est: int | None = None
    queue_sts: int | None = None
    project_id: str | None = None
    profile_id: str | None = None
    task_id: str | None = None
    subtask_id: str | None = None
    subtask_name: str | None = None
    gcode_file: str | None = None
    stg: list[Any] | None = None
    stg_cur: int | None = None
    print_type: str | None = None
    home_flag: int | None = None
    mc_print_line_number: str | None = None
    mc_print_sub_stage: int | None = None
    sdcard: bool | None = None
    force_upgrade: bool | None = None
    mess_production_state: str | None = None
    layer_num: int | None = None
    total_layer_num: int | None = None
    s_obj: list[Any] | None = None
    fan_gear: int | None = None
    hms: list[Any] | None = None
    online: Online | None = None
    ams: AMS | None = None
    ipcam: IPCam | None = None
    vt_tray: VTTray | None = None
    lights_report: list[LightsReport] | None = None
    upgrade_state: UpgradeState | None = None
    command: str | None = None
    msg: int | None = None
    sequence_id: str | None = None
