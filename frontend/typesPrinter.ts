export type CommandType =
    | "chamber_light"
    | "extruder_temp"
    | "bed_temp"
    | "print_speed"
    | "fan_aux"
    | "fan_chamber"
    | "fan_part"
    | "move_x"
    | "move_y"
    | "move_z"
    | "move_e"
    | "move_home"
    | "stop_print"
    | "pause_print"
    | "resume_print"
    | "load_filament"
    | "unload_filament"
    | "force_refresh"
    | "calibrate"
    | "upload_file";

export abstract class PrinterCommand {
    constructor(readonly type: CommandType) {}
}

export class ChamberLight extends PrinterCommand {
    constructor(readonly enable: boolean) {
        super("chamber_light");
    }
}

abstract class Temperature extends PrinterCommand {
    constructor(
        type: CommandType,
        readonly temperature: number,
    ) {
        super(type);
    }
}

export class ExtruderTemp extends Temperature {
    constructor(temperature: number) {
        super("extruder_temp", temperature);
    }
}

export class BedTemp extends Temperature {
    constructor(temperature: number) {
        super("bed_temp", temperature);
    }
}

export class PrintSpeed extends PrinterCommand {
    constructor(readonly speed: 1 | 2 | 3 | 4) {
        super("print_speed");
    }
}

abstract class FanSpeed extends PrinterCommand {
    constructor(
        type: CommandType,
        readonly speed: number,
    ) {
        super(type);
    }
}

export class AuxFanSpeed extends FanSpeed {
    constructor(speed: number) {
        super("fan_aux", speed);
    }
}

export class ChamberFanSpeed extends FanSpeed {
    constructor(speed: number) {
        super("fan_chamber", speed);
    }
}

export class PartFanSpeed extends FanSpeed {
    constructor(speed: number) {
        super("fan_part", speed);
    }
}

abstract class Move extends PrinterCommand {
    constructor(
        type: CommandType,
        readonly distance: number,
    ) {
        super(type);
    }
}

export class MoveX extends Move {
    constructor(distance: number) {
        super("move_x", distance);
    }
}

export class MoveY extends Move {
    constructor(distance: number) {
        super("move_y", distance);
    }
}

export class MoveZ extends Move {
    constructor(distance: number) {
        super("move_z", distance);
    }
}

export class MoveE extends Move {
    constructor(distance: number) {
        super("move_e", distance);
    }
}

export class MoveHome extends PrinterCommand {
    constructor() {
        super("move_home");
    }
}

export class StopPrint extends PrinterCommand {
    constructor() {
        super("stop_print");
    }
}

export class PausePrint extends PrinterCommand {
    constructor() {
        super("pause_print");
    }
}

export class ResumePrint extends PrinterCommand {
    constructor() {
        super("resume_print");
    }
}

export class FilamentLoad extends PrinterCommand {
    constructor() {
        super("load_filament");
    }
}

export class FilamentUnload extends PrinterCommand {
    constructor() {
        super("unload_filament");
    }
}

export class ForceRefresh extends PrinterCommand {
    constructor() {
        super("force_refresh");
    }
}

export class Calibration extends PrinterCommand {
    constructor(
        readonly bed_levelling: boolean,
        readonly motor_noise_cancellation: boolean,
        readonly vibration_compensation: boolean,
    ) {
        super("calibrate");
    }
}

export class PrintFile extends PrinterCommand {
    constructor(
        readonly file: string,
        readonly file_name: string,
    ) {
        super("upload_file");
    }
}
