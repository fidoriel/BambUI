<script lang="ts">
    import { onMount, onDestroy, tick } from "svelte";
    import { useRoute } from "@dvcol/svelte-simple-router/router";
    import { getBackendUrl } from "$lib/utils.js";
    import * as Tooltip from "$lib/components/ui/tooltip";
    import extruderIllustration from "../assets/extruder.svg";
    import { Card, CardContent } from "$lib/components/ui/card";
    import { Button } from "$lib/components/ui/button";
    import { Slider } from "$lib/components/ui/slider";
    import { Home } from "lucide-svelte";
    import { Progress } from "$lib/components/ui/progress";
    import { AspectRatio } from "$lib/components/ui/aspect-ratio";
    import { Fan } from "lucide-svelte";
    import { CirclePause } from "lucide-svelte";
    import { CirclePlay } from "lucide-svelte";
    import { CircleStop } from "lucide-svelte";
    import { Lightbulb } from "lucide-svelte";
    import { Cctv, RefreshCw } from "lucide-svelte";
    import { CircleGauge, Activity } from "lucide-svelte";
    import { File, Layers, Clock, Thermometer } from "lucide-svelte";
    import type { PrinterStatus } from "./printerModel";
    import { toast } from "svelte-sonner";
    import * as AlertDialog from "$lib/components/ui/alert-dialog/index.js";
    import { Label } from "$lib/components/ui/label/index.js";
    import { Switch } from "$lib/components/ui/switch/index.js";
    import { ChevronsLeftRightEllipsis } from "lucide-svelte";
    import { AmsStatus } from "$lib/components/ui/ams/index.js";

    import {
        AuxFanSpeed,
        ChamberFanSpeed,
        ChamberLight,
        FilamentLoad,
        FilamentUnload,
        ForceRefresh,
        MoveE,
        MoveHome,
        MoveX,
        MoveY,
        MoveZ,
        PartFanSpeed,
        PausePrint,
        PrinterCommand,
        PrintFile,
        PrintSpeed,
        ResumePrint,
        StopPrint,
        Calibration,
    } from "../typesPrinter";
    import type { PrinterResponse } from "../typesApi";

    const speedModes = ["Silent", "Standard", "Sport", "Ludicrous"];

    const { route, location, routing } = useRoute();
    const queryParams = $derived(location.query);
    const printerId = queryParams["printerId"];

    let printerStatusPulse = $state(false);
    let printerSignOfLife = $state(false);
    let imagePulse = $state(false);
    let imageSignOfLife = $state(false);

    let imageUrl = $state<string | null>(null);
    let ws = $state<WebSocket | null>(null);
    let connectionError = $state<string | null>(null);
    let printerStatus = $state<PrinterStatus | undefined>(undefined);
    let printerLightOn = $state<boolean>(false);

    // Websocket States
    let reconnectAttempts = 0;
    let maxReconnectAttempts = 5;
    let reconnectTimer: number;
    let isConnecting = false;

    const backendUrl = getBackendUrl();

    let printer = $state<PrinterResponse | null>(null);

    function toPercent(value: number): number {
        // value  [0, 15] → 0‑100 %
        return Math.round(value / 1.5) * 10;
    }

    function scaleSliderToBackend(value: number, coefficient: number): number {
        // UI → 0‑15, Backend → 0‑255 (coefficient × value)
        const scaled = Math.round(value * coefficient);
        return Math.min(scaled, 255);
    }

    function createSmartControl<T>(getBackendValue: () => T, onCommit: (value: T) => void) {
        let localValue = $state(getBackendValue());
        let isInteracting = $state(false);
        let timeout: number;
        let skipNextChange = false;

        $effect(() => {
            if (!isInteracting) {
                skipNextChange = true;
                localValue = getBackendValue();
                tick().then(() => {
                    skipNextChange = false;
                });
            }
        });

        onDestroy(() => {
            clearTimeout(timeout);
        });

        return {
            get value() {
                return localValue;
            },

            onChange(value: T) {
                if (skipNextChange) {
                    // Reset just in case several rapid backend updates happen
                    skipNextChange = false;
                    return;
                }
                localValue = value;
                isInteracting = true;
                clearTimeout(timeout);
            },

            onCommit(value: T) {
                localValue = value;
                onCommit(value);
                timeout = setTimeout(() => {
                    isInteracting = false;
                }, 7000);
            },
        };
    }

    const controls = {
        chamberLight: createSmartControl(
            () => printerStatus?.lights_report?.[0]?.mode === "on",
            (v) => sendWsCommand(new ChamberLight(v)),
        ),
        partFan: createSmartControl(
            () => Number(printerStatus?.cooling_fan_speed || 0),
            (v) => sendWsCommand(new PartFanSpeed(scaleSliderToBackend(v, 15))),
        ),
        chamberFan: createSmartControl(
            () => Number(printerStatus?.big_fan2_speed || 0),
            (v) => sendWsCommand(new ChamberFanSpeed(scaleSliderToBackend(v, 17))),
        ),
        auxFan: createSmartControl(
            () => Number(printerStatus?.big_fan1_speed || 0),
            (v) => sendWsCommand(new AuxFanSpeed(scaleSliderToBackend(v, 17))),
        ),
    };

    onMount(async () => {
        try {
            const response = await fetch(`${backendUrl}/api/printer/${printerId}`);
            if (!response.ok) throw new Error("Failed to fetch printers");
            printer = (await response.json()) as PrinterResponse;
            console.log(printer);
        } catch (error) {
            console.error("Error fetching printers:", error);
        }
    });

    function connect() {
        if (isConnecting) return;
        isConnecting = true;
        ws = new WebSocket(`${backendUrl}/ws/printer/${printerId}`);

        ws.onmessage = (event) => {
            reconnectAttempts = 0; // Reset on successful message
            const message = JSON.parse(event.data);
            if (message.type === "jpeg_image") {
                imageSignOfLife = true;
                const binaryData = atob(message.image);
                const bytes = new Uint8Array(binaryData.length);
                for (let i = 0; i < binaryData.length; i++) {
                    bytes[i] = binaryData.charCodeAt(i);
                }
                const blob = new Blob([bytes], { type: "image/jpeg" });

                if (imageUrl) {
                    URL.revokeObjectURL(imageUrl);
                }
                imageUrl = URL.createObjectURL(blob);
                imagePulse = true;
                setTimeout(() => (imagePulse = false), 500);
            } else if (message.type === "printer_status") {
                printerSignOfLife = true;
                printerStatus = message.data as PrinterStatus;
                printerLightOn = printerStatus?.lights_report?.[0]?.mode === "on";

                printerStatusPulse = true;
                setTimeout(() => (printerStatusPulse = false), 500);
            } else if (message.type === "error") {
                toast(message.message);
            } else if (message.type === "message") {
                toast(message.message);
            }
        };

        ws.onerror = (error) => {
            connectionError = "Connection unexpectedly closed, reconnecting...";
            console.error("WebSocket error:", error);
        };

        ws.onclose = (event) => {
            isConnecting = false;
            printerSignOfLife = false;
            imageSignOfLife = false;
            if (event.code === 4004) {
                connectionError = "Invalid printer name";
                return;
            }

            if (reconnectAttempts < maxReconnectAttempts) {
                const backoffDelay = Math.min(1000 * Math.pow(2, reconnectAttempts), 30000);
                reconnectTimer = setTimeout(() => {
                    reconnectAttempts++;
                    connect();
                }, backoffDelay);
            }
        };

        ws.onopen = () => {
            isConnecting = false;
            connectionError = null;
        };
    }

    onMount(() => {
        connect();
    });

    onDestroy(() => {
        if (ws) {
            ws.close();
        }
        if (imageUrl) {
            URL.revokeObjectURL(imageUrl);
        }
        clearTimeout(reconnectTimer);
    });

    function sendWsCommand(request: PrinterCommand) {
        ws?.send(JSON.stringify(request));
    }

    let file_to_print = $state<FileList | null>(null);

    $effect(() => {
        if (file_to_print) {
            for (const file of file_to_print || []) {
                console.log(`Uploading ${file.name}: ${file.size} bytes`);
                const reader = new FileReader();
                reader.onloadend = () => {
                    if (!reader.result || typeof reader.result != "string") {
                        alert("invalid file");
                        return;
                    }
                    const base64String = reader.result.split(",")[1];
                    sendWsCommand(new PrintFile(base64String, file.name));
                };
                reader.readAsDataURL(file);
            }
        }
    });
</script>

<div class="grid grid-flow-row-dense auto-rows-min grid-cols-1 gap-4 overflow-hidden p-4 md:grid-cols-5">
    <div class="flex flex-col space-y-4 md:col-span-3">
        <!-- Camera Feed -->
        <div class="w-full">
            <AspectRatio ratio={16 / 9}>
                {#if connectionError}
                    <div>{connectionError}</div>
                {:else if imageUrl}
                    <img src={imageUrl} alt="Printer camera feed" class="h-full w-full rounded-md object-cover" />
                {:else}
                    <div>Connecting to printer camera...</div>
                {/if}
            </AspectRatio>
        </div>

        <!-- Print Status -->
        <Card class="bg-900">
            <CardContent class="p-4">
                <div class="flex flex-row flex-wrap items-center gap-4 md:gap-8">
                    <!-- File Name -->
                    <div class="flex flex-col items-start" title="Current File">
                        <span class="text-sm text-gray-400" aria-hidden="true"><File /></span>
                        <span class="text-sm font-medium" role="status">
                            {printerStatus?.gcode_file || "No file loaded"}
                        </span>
                    </div>

                    <!-- Status -->
                    <div class="flex flex-col items-start" title="Print Status">
                        <span class="text-sm text-gray-400" aria-hidden="true"><Activity /></span>
                        <span class="text-sm font-medium" role="status">
                            {printerStatus?.print_type || "Idle"}
                        </span>
                    </div>

                    <!-- Layer Info -->
                    <div class="flex flex-col items-start" title="Layer Progress">
                        <span class="text-sm text-gray-400" aria-hidden="true"><Layers /></span>
                        <span class="text-sm font-medium" role="status">
                            {printerStatus?.layer_num || 0}/{printerStatus?.total_layer_num || 0}
                        </span>
                    </div>

                    <!-- Time Remaining -->
                    <div class="flex flex-col items-start" title="Time Remaining">
                        <span class="text-sm text-gray-400" aria-hidden="true"><Clock /></span>
                        <span class="text-sm font-medium" role="status">
                            {printerStatus?.mc_remaining_time || "--"}
                        </span>
                    </div>
                    <div class="flex flex-col items-start" title="Time Remaining">
                        <Button variant="outline"><Label for="file">Print File</Label></Button>
                        <input
                            class="hidden"
                            accept=".3mf"
                            bind:files={file_to_print}
                            id="file"
                            name="file"
                            type="file"
                        />
                    </div>

                    <!-- Print Progress -->
                    <Progress value={printerStatus?.mc_percent || 0} max={100} aria-label="Print progress" />
                </div>
                <div class="mt-4 flex flex-row items-center gap-2">
                    <h3 class="mr-auto text-lg">Status {printerStatus?.print_type} {printerStatus?.mc_percent}%</h3>

                    <Tooltip.Provider>
                        <Tooltip.Root>
                            <Tooltip.Trigger>
                                <Button
                                    variant="outline"
                                    onclick={() => {
                                        sendWsCommand(new PausePrint());
                                    }}><CirclePause /></Button
                                ></Tooltip.Trigger
                            >
                            <Tooltip.Content>
                                <p>Pause</p>
                            </Tooltip.Content>
                        </Tooltip.Root>
                    </Tooltip.Provider>

                    <AlertDialog.Root>
                        <AlertDialog.Trigger>
                            <Tooltip.Provider>
                                <Tooltip.Root>
                                    <Tooltip.Trigger>
                                        <Button variant="outline">
                                            <CircleStop />
                                        </Button>
                                    </Tooltip.Trigger>
                                    <Tooltip.Content>
                                        <p>Stop</p>
                                    </Tooltip.Content>
                                </Tooltip.Root>
                            </Tooltip.Provider></AlertDialog.Trigger
                        >
                        <AlertDialog.Content>
                            <AlertDialog.Header>
                                <AlertDialog.Title>Are you absolutely sure to Stop the Print?</AlertDialog.Title>
                                <AlertDialog.Description>
                                    This action cannot be undone. The print cannot be resumed.
                                </AlertDialog.Description>
                            </AlertDialog.Header>
                            <AlertDialog.Footer>
                                <AlertDialog.Cancel>Cancel</AlertDialog.Cancel>
                                <AlertDialog.Action
                                    onclick={() => {
                                        sendWsCommand(new StopPrint());
                                    }}
                                >
                                    Stop Print
                                </AlertDialog.Action>
                            </AlertDialog.Footer>
                        </AlertDialog.Content>
                    </AlertDialog.Root>

                    <Tooltip.Provider>
                        <Tooltip.Root>
                            <Tooltip.Trigger>
                                <Button
                                    variant="outline"
                                    onclick={() => {
                                        sendWsCommand(new ResumePrint());
                                    }}
                                >
                                    <CirclePlay />
                                </Button></Tooltip.Trigger
                            >
                            <Tooltip.Content>
                                <p>Resume</p>
                            </Tooltip.Content>
                        </Tooltip.Root>
                    </Tooltip.Provider>
                </div>
            </CardContent>
        </Card>
    </div>
    <div class="flex flex-col space-y-4 md:col-span-2">
        <div class="flex items-center justify-between">
            <h1 class="text-2xl font-bold">{printerId}</h1>
            <div class="flex items-center space-x-4">
                <ChevronsLeftRightEllipsis
                    class={printerStatusPulse ? "animate-ping" : ""}
                    color={printerSignOfLife ? "green" : "red"}
                />
                <Cctv class={imagePulse ? "animate-ping" : ""} color={imageSignOfLife ? "green" : "red"} />
                <Button
                    variant="outline"
                    onclick={() => {
                        sendWsCommand(new ForceRefresh());
                    }}><RefreshCw /></Button
                >
            </div>
        </div>
        <!-- First-Section: Unified Controls Card -->
        <Card class="bg-900">
            <CardContent class="p-4">
                <!-- Desktop: 4-column layout with vertical dividers -->
                <div class="hidden min-[1752px]:grid min-[1752px]:grid-cols-[auto_1px_1fr_1px_auto_1px_auto] min-[1752px]:gap-4">
                    <!-- Column 1: Status (Temps, Light, Speed) -->
                    <div class="flex flex-col justify-between gap-3">
                        <div class="flex items-center gap-3">
                            <Thermometer class="h-5 w-5 shrink-0 text-muted-foreground" />
                            <div>
                                <p class="text-xs text-muted-foreground">Nozzle</p>
                                <p class="text-lg font-semibold">{Math.round(printerStatus?.nozzle_temper ?? 0)}/{printerStatus?.nozzle_target_temper}°C</p>
                            </div>
                        </div>
                        <div class="flex items-center gap-3">
                            <Thermometer class="h-5 w-5 shrink-0 text-muted-foreground" />
                            <div>
                                <p class="text-xs text-muted-foreground">Bed</p>
                                <p class="text-lg font-semibold">{Math.round(printerStatus?.bed_temper ?? 0)}/{printerStatus?.bed_target_temper}°C</p>
                            </div>
                        </div>
                        {#if printer?.supports_chamber_temp}
                            <div class="flex items-center gap-3">
                                <Thermometer class="h-5 w-5 shrink-0 text-muted-foreground" />
                                <div>
                                    <p class="text-xs text-muted-foreground">Chamber</p>
                                    <p class="text-lg font-semibold">{Math.round(printerStatus?.chamber_temper ?? 0)}°C</p>
                                </div>
                            </div>
                        {/if}
                        <hr class="border-border" />
                        <div class="flex items-center gap-3">
                            <Lightbulb class="h-5 w-5 shrink-0 text-muted-foreground" />
                            <Switch
                                id="printer-light"
                                checked={controls.chamberLight.value}
                                onCheckedChange={(enabled: boolean) => {
                                    controls.chamberLight.onChange(enabled);
                                    controls.chamberLight.onCommit(enabled);
                                }}
                            />
                        </div>
                        <hr class="border-border" />
                        <AlertDialog.Root>
                            <AlertDialog.Trigger>
                                <button class="flex items-center gap-3 rounded-md p-1 text-left hover:bg-muted/50 transition-colors">
                                    <CircleGauge class="h-5 w-5 shrink-0 text-muted-foreground" />
                                    <div>
                                        <p class="text-xs text-muted-foreground">Speed</p>
                                        <p class="text-lg font-semibold">{speedModes[(printerStatus?.spd_lvl ?? 2) - 1] || "Normal"}</p>
                                    </div>
                                </button>
                            </AlertDialog.Trigger>
                            <AlertDialog.Content>
                                <AlertDialog.Header>
                                    <AlertDialog.Title>Print Speed</AlertDialog.Title>
                                    <AlertDialog.Description>Select the print speed mode.</AlertDialog.Description>
                                </AlertDialog.Header>
                                <div class="grid grid-cols-2 gap-2 py-4">
                                    {#each speedModes as mode, i}
                                        <Button
                                            variant={(printerStatus?.spd_lvl ?? 2) === i + 1 ? "default" : "outline"}
                                            onclick={() => sendWsCommand(new PrintSpeed((i + 1) as 1 | 2 | 3 | 4))}
                                            class="w-full"
                                        >{mode}</Button>
                                    {/each}
                                </div>
                                <AlertDialog.Footer>
                                    <AlertDialog.Cancel>Close</AlertDialog.Cancel>
                                </AlertDialog.Footer>
                            </AlertDialog.Content>
                        </AlertDialog.Root>
                    </div>

                    <!-- Vertical Divider -->
                    <div class="bg-border"></div>

                    <!-- Column 2: Movement (XY D-pad + Z row) -->
                    <div class="flex flex-col items-center justify-between gap-4">
                        <!-- XY D-pad: SVG with clickable wedge buttons -->
                        <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
                        <svg viewBox="0 0 249 249" class="h-[220px] w-[220px]" fill="none" xmlns="http://www.w3.org/2000/svg">
                            <style>
                                .dpad-wedge { fill: var(--dpad-fill); cursor: pointer; transition: fill 0.15s; }
                                .dpad-wedge:hover { fill: var(--dpad-fill-hover); }
                                .dpad-label { fill: var(--dpad-text); font-size: 11px; font-weight: 600; font-family: sans-serif; pointer-events: none; user-select: none; }
                                .dpad-home { fill: var(--dpad-home); cursor: pointer; transition: fill 0.15s; }
                                .dpad-home:hover { fill: var(--dpad-home-hover); }
                            </style>
                            <!-- Outer ring: Y+10 (top) -->
                            <path on:click={() => sendWsCommand(new MoveY(+10))} role="button" tabindex="0" d="M124.5 0C157.273 0 187.088 12.6638 209.32 33.3643L183.279 59.4053C167.854 45.4795 147.418 37 125 37C102.328 37 81.681 45.673 66.1963 59.8818L39.6787 33.3643C61.9107 12.6635 91.7265 0 124.5 0Z" class="dpad-wedge" />
                            <text x="124.5" y="22" text-anchor="middle" class="dpad-label">Y+10</text>

                            <!-- Outer ring: X-10 (left) -->
                            <path on:click={() => sendWsCommand(new MoveX(-10))} role="button" tabindex="0" d="M60.5537 65.5537C46.5389 80.9979 38 101.502 38 124C38 146.418 46.4795 166.854 60.4053 182.279L33.3643 209.32C12.6638 187.088 0 157.273 0 124.5C0 91.392 12.9237 61.3029 34.001 39.001L60.5537 65.5537Z" class="dpad-wedge" />
                            <text x="20" y="128" text-anchor="middle" class="dpad-label">X-10</text>

                            <!-- Outer ring: X+10 (right) -->
                            <path on:click={() => sendWsCommand(new MoveX(+10))} role="button" tabindex="0" d="M214.998 39.001C236.076 61.303 249 91.3918 249 124.5C249 157.274 236.336 187.088 215.635 209.32L189.117 182.803C203.326 167.318 212 146.672 212 124C212 101.247 203.265 80.5351 188.966 65.0322L214.998 39.001Z" class="dpad-wedge" />
                            <text x="229" y="128" text-anchor="middle" class="dpad-label">X+10</text>

                            <!-- Outer ring: Y-10 (bottom) -->
                            <path on:click={() => sendWsCommand(new MoveY(-10))} role="button" tabindex="0" d="M66.0322 187.966C81.5351 202.265 102.247 211 125 211C147.498 211 168.001 202.46 183.445 188.445L209.998 214.998C187.696 236.075 157.608 249 124.5 249C91.3918 249 61.303 236.076 39.001 214.998L66.0322 187.966Z" class="dpad-wedge" />
                            <text x="124.5" y="234" text-anchor="middle" class="dpad-label">Y-10</text>

                            <!-- Inner wedge: Y+1 (top) -->
                            <path on:click={() => sendWsCommand(new MoveY(+1))} role="button" tabindex="0" d="M125 45C145.208 45 163.643 52.5887 177.613 65.0703L124.5 118.186L71.8584 65.5439C85.8905 52.7801 104.537 45 125 45Z" class="dpad-wedge" />
                            <text x="124.5" y="68" text-anchor="middle" class="dpad-label">Y+1</text>

                            <!-- Inner wedge: X-1 (left) -->
                            <path on:click={() => sendWsCommand(new MoveX(-1))} role="button" tabindex="0" d="M118.843 123.843L66.0703 176.613C53.5887 162.643 46 144.208 46 124C46 103.711 53.6482 85.209 66.2188 71.2188L118.843 123.843Z" class="dpad-wedge" />
                            <text x="72" y="128" text-anchor="middle" class="dpad-label">X-1</text>

                            <!-- Inner wedge: X+1 (right) -->
                            <path on:click={() => sendWsCommand(new MoveX(+1))} role="button" tabindex="0" d="M183.305 70.6943C196.158 84.7451 204 103.456 204 124C204 144.463 196.219 163.109 183.455 177.141L130.157 123.843L183.305 70.6943Z" class="dpad-wedge" />
                            <text x="177" y="128" text-anchor="middle" class="dpad-label">X+1</text>

                            <!-- Inner wedge: Y-1 (bottom) -->
                            <path on:click={() => sendWsCommand(new MoveY(-1))} role="button" tabindex="0" d="M177.78 182.78C163.79 195.351 145.289 203 125 203C104.456 203 85.7451 195.158 71.6943 182.305L124.5 129.5L177.78 182.78Z" class="dpad-wedge" />
                            <text x="124.5" y="190" text-anchor="middle" class="dpad-label">Y-1</text>

                            <!-- Center: Home button -->
                            <circle on:click={() => sendWsCommand(new MoveHome())} role="button" tabindex="0" cx="124.5" cy="124" r="28" class="dpad-home" stroke="hsl(136,64%,38%)" stroke-width="2" />
                            <g pointer-events="none" transform="translate(124.5, 124)">
                                <path d="M0-10l-9 7.5v9.5a1.5 1.5 0 001.5 1.5h5v-5h5v5h5a1.5 1.5 0 001.5-1.5v-9.5z" fill="none" stroke="hsl(136, 64%, 38%)" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" />
                            </g>
                        </svg>
                        <!-- Z Row -->
                        <div class="flex gap-2">
                            <Button onclick={() => sendWsCommand(new MoveZ(+10))} variant="outline" class="h-8 w-14 text-xs">Z+10</Button>
                            <Button onclick={() => sendWsCommand(new MoveZ(+1))} variant="outline" class="h-8 w-14 text-xs">Z+1</Button>
                            <Button onclick={() => sendWsCommand(new MoveZ(-1))} variant="outline" class="h-8 w-14 text-xs">Z-1</Button>
                            <Button onclick={() => sendWsCommand(new MoveZ(-10))} variant="outline" class="h-8 w-14 text-xs">Z-10</Button>
                        </div>
                    </div>

                    <!-- Vertical Divider -->
                    <div class="bg-border"></div>

                    <!-- Column 3: Filament Controls -->
                    <div class="flex flex-col items-center justify-center gap-2">
                        <Button onclick={() => sendWsCommand(new MoveE(-10))} variant="outline" class="h-8 w-20 text-xs">Retract</Button>
                        <img src={extruderIllustration} alt="Extruder" class="h-20 w-[30px] object-contain opacity-70" />
                        <Button onclick={() => sendWsCommand(new MoveE(10))} variant="outline" class="h-8 w-20 text-xs">Extrude</Button>
                        <hr class="w-full border-border" />
                        <Button onclick={() => sendWsCommand(new FilamentLoad())} variant="outline" class="h-8 w-20 text-xs">Load</Button>
                        <Button onclick={() => sendWsCommand(new FilamentUnload())} variant="outline" class="h-8 w-20 text-xs">Unload</Button>
                    </div>

                    <!-- Vertical Divider -->
                    <div class="bg-border"></div>

                    <!-- Column 4: Calibration -->
                    <div class="flex flex-col items-center justify-center gap-2">
                        <Button onclick={() => sendWsCommand(new Calibration(true, false, false))} variant="outline" class="h-8 w-28 text-xs">Level Bed</Button>
                        <Button onclick={() => sendWsCommand(new Calibration(true, true, true))} variant="outline" class="h-8 w-28 text-xs">Full Calibration</Button>
                    </div>
                </div>

                <!-- Mobile/Tablet: stacked single-column layout -->
                <div class="flex flex-col gap-4 min-[1752px]:hidden">
                    <!-- Status Row -->
                    <div class="grid grid-cols-2 gap-3">
                        <div class="flex items-center gap-2">
                            <Thermometer class="h-4 w-4 shrink-0 text-muted-foreground" />
                            <div>
                                <p class="text-xs text-muted-foreground">Nozzle</p>
                                <p class="text-base font-semibold">{Math.round(printerStatus?.nozzle_temper ?? 0)}/{printerStatus?.nozzle_target_temper}°C</p>
                            </div>
                        </div>
                        <div class="flex items-center gap-2">
                            <Thermometer class="h-4 w-4 shrink-0 text-muted-foreground" />
                            <div>
                                <p class="text-xs text-muted-foreground">Bed</p>
                                <p class="text-base font-semibold">{Math.round(printerStatus?.bed_temper ?? 0)}/{printerStatus?.bed_target_temper}°C</p>
                            </div>
                        </div>
                        {#if printer?.supports_chamber_temp}
                            <div class="flex items-center gap-2">
                                <Thermometer class="h-4 w-4 shrink-0 text-muted-foreground" />
                                <div>
                                    <p class="text-xs text-muted-foreground">Chamber</p>
                                    <p class="text-base font-semibold">{Math.round(printerStatus?.chamber_temper ?? 0)}°C</p>
                                </div>
                            </div>
                        {/if}
                        <div class="flex items-center gap-2">
                            <Lightbulb class="h-4 w-4 shrink-0 text-muted-foreground" />
                            <Switch
                                id="printer-light-mobile"
                                checked={controls.chamberLight.value}
                                onCheckedChange={(enabled: boolean) => {
                                    controls.chamberLight.onChange(enabled);
                                    controls.chamberLight.onCommit(enabled);
                                }}
                            />
                        </div>
                    </div>
                    <AlertDialog.Root>
                        <AlertDialog.Trigger>
                            <button class="flex items-center gap-2 rounded-md p-1 text-left hover:bg-muted/50 transition-colors">
                                <CircleGauge class="h-4 w-4 shrink-0 text-muted-foreground" />
                                <span class="text-xs text-muted-foreground">Speed</span>
                                <span class="text-sm font-semibold">{speedModes[(printerStatus?.spd_lvl ?? 2) - 1] || "Normal"}</span>
                            </button>
                        </AlertDialog.Trigger>
                        <AlertDialog.Content>
                            <AlertDialog.Header>
                                <AlertDialog.Title>Print Speed</AlertDialog.Title>
                                <AlertDialog.Description>Select the print speed mode.</AlertDialog.Description>
                            </AlertDialog.Header>
                            <div class="grid grid-cols-2 gap-2 py-4">
                                {#each speedModes as mode, i}
                                    <Button
                                        variant={(printerStatus?.spd_lvl ?? 2) === i + 1 ? "default" : "outline"}
                                        onclick={() => sendWsCommand(new PrintSpeed((i + 1) as 1 | 2 | 3 | 4))}
                                        class="w-full"
                                    >{mode}</Button>
                                {/each}
                            </div>
                            <AlertDialog.Footer>
                                <AlertDialog.Cancel>Close</AlertDialog.Cancel>
                            </AlertDialog.Footer>
                        </AlertDialog.Content>
                    </AlertDialog.Root>

                    <hr class="border-border" />

                    <!-- XY D-pad (Mobile) -->
                    <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
                    <svg viewBox="0 0 249 249" class="mx-auto h-[180px] w-[180px]" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <style>
                            .dpad-wedge { fill: var(--dpad-fill); cursor: pointer; transition: fill 0.15s; }
                            .dpad-wedge:hover { fill: var(--dpad-fill-hover); }
                            .dpad-label { fill: var(--dpad-text); font-size: 11px; font-weight: 600; font-family: sans-serif; pointer-events: none; user-select: none; }
                            .dpad-home { fill: var(--dpad-home); cursor: pointer; transition: fill 0.15s; }
                            .dpad-home:hover { fill: var(--dpad-home-hover); }
                        </style>
                        <path on:click={() => sendWsCommand(new MoveY(+10))} role="button" tabindex="0" d="M124.5 0C157.273 0 187.088 12.6638 209.32 33.3643L183.279 59.4053C167.854 45.4795 147.418 37 125 37C102.328 37 81.681 45.673 66.1963 59.8818L39.6787 33.3643C61.9107 12.6635 91.7265 0 124.5 0Z" class="dpad-wedge" />
                        <text x="124.5" y="22" text-anchor="middle" class="dpad-label">Y+10</text>

                        <path on:click={() => sendWsCommand(new MoveX(-10))} role="button" tabindex="0" d="M60.5537 65.5537C46.5389 80.9979 38 101.502 38 124C38 146.418 46.4795 166.854 60.4053 182.279L33.3643 209.32C12.6638 187.088 0 157.273 0 124.5C0 91.392 12.9237 61.3029 34.001 39.001L60.5537 65.5537Z" class="dpad-wedge" />
                        <text x="20" y="128" text-anchor="middle" class="dpad-label">X-10</text>

                        <path on:click={() => sendWsCommand(new MoveX(+10))} role="button" tabindex="0" d="M214.998 39.001C236.076 61.303 249 91.3918 249 124.5C249 157.274 236.336 187.088 215.635 209.32L189.117 182.803C203.326 167.318 212 146.672 212 124C212 101.247 203.265 80.5351 188.966 65.0322L214.998 39.001Z" class="dpad-wedge" />
                        <text x="229" y="128" text-anchor="middle" class="dpad-label">X+10</text>

                        <path on:click={() => sendWsCommand(new MoveY(-10))} role="button" tabindex="0" d="M66.0322 187.966C81.5351 202.265 102.247 211 125 211C147.498 211 168.001 202.46 183.445 188.445L209.998 214.998C187.696 236.075 157.608 249 124.5 249C91.3918 249 61.303 236.076 39.001 214.998L66.0322 187.966Z" class="dpad-wedge" />
                        <text x="124.5" y="234" text-anchor="middle" class="dpad-label">Y-10</text>

                        <path on:click={() => sendWsCommand(new MoveY(+1))} role="button" tabindex="0" d="M125 45C145.208 45 163.643 52.5887 177.613 65.0703L124.5 118.186L71.8584 65.5439C85.8905 52.7801 104.537 45 125 45Z" class="dpad-wedge" />
                        <text x="124.5" y="68" text-anchor="middle" class="dpad-label">Y+1</text>

                        <path on:click={() => sendWsCommand(new MoveX(-1))} role="button" tabindex="0" d="M118.843 123.843L66.0703 176.613C53.5887 162.643 46 144.208 46 124C46 103.711 53.6482 85.209 66.2188 71.2188L118.843 123.843Z" class="dpad-wedge" />
                        <text x="72" y="128" text-anchor="middle" class="dpad-label">X-1</text>

                        <path on:click={() => sendWsCommand(new MoveX(+1))} role="button" tabindex="0" d="M183.305 70.6943C196.158 84.7451 204 103.456 204 124C204 144.463 196.219 163.109 183.455 177.141L130.157 123.843L183.305 70.6943Z" class="dpad-wedge" />
                        <text x="177" y="128" text-anchor="middle" class="dpad-label">X+1</text>

                        <path on:click={() => sendWsCommand(new MoveY(-1))} role="button" tabindex="0" d="M177.78 182.78C163.79 195.351 145.289 203 125 203C104.456 203 85.7451 195.158 71.6943 182.305L124.5 129.5L177.78 182.78Z" class="dpad-wedge" />
                        <text x="124.5" y="190" text-anchor="middle" class="dpad-label">Y-1</text>

                        <circle on:click={() => sendWsCommand(new MoveHome())} role="button" tabindex="0" cx="124.5" cy="124" r="28" class="dpad-home" stroke="hsl(136,64%,38%)" stroke-width="2" />
                        <g pointer-events="none" transform="translate(124.5, 124)">
                            <path d="M0-10l-9 7.5v9.5a1.5 1.5 0 001.5 1.5h5v-5h5v5h5a1.5 1.5 0 001.5-1.5v-9.5z" fill="none" stroke="hsl(136, 64%, 38%)" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" />
                        </g>
                    </svg>

                    <!-- Z Row (Mobile) -->
                    <div class="flex justify-center gap-1">
                        <Button onclick={() => sendWsCommand(new MoveZ(+10))} variant="outline" class="h-8 w-12 text-xs">Z+10</Button>
                        <Button onclick={() => sendWsCommand(new MoveZ(+1))} variant="outline" class="h-8 w-12 text-xs">Z+1</Button>
                        <Button onclick={() => sendWsCommand(new MoveZ(-1))} variant="outline" class="h-8 w-12 text-xs">Z-1</Button>
                        <Button onclick={() => sendWsCommand(new MoveZ(-10))} variant="outline" class="h-8 w-12 text-xs">Z-10</Button>
                    </div>

                    <hr class="border-border" />

                    <!-- Filament Controls (Mobile) -->
                    <div class="grid grid-cols-2 gap-2">
                        <Button onclick={() => sendWsCommand(new MoveE(-10))} variant="outline" class="h-8 text-xs">Retract</Button>
                        <Button onclick={() => sendWsCommand(new MoveE(10))} variant="outline" class="h-8 text-xs">Extrude</Button>
                        <Button onclick={() => sendWsCommand(new FilamentLoad())} variant="outline" class="h-8 text-xs">Load</Button>
                        <Button onclick={() => sendWsCommand(new FilamentUnload())} variant="outline" class="h-8 text-xs">Unload</Button>
                    </div>

                    <hr class="border-border" />

                    <!-- Calibration (Mobile) -->
                    <div class="grid grid-cols-2 gap-2">
                        <Button onclick={() => sendWsCommand(new Calibration(true, false, false))} variant="outline" class="h-8 text-xs">Level Bed</Button>
                        <Button onclick={() => sendWsCommand(new Calibration(true, true, true))} variant="outline" class="h-8 text-xs">Full Calibration</Button>
                    </div>
                </div>
            </CardContent>
        </Card>


        <!-- Fan Controls -->
        <Card>
            <CardContent class="p-4">
                <div class="grid grid-cols-1 gap-4">
                    <div class="bg-400 rounded-lg p-3">
                        <div class="mb-2 flex justify-between">
                            <div class="flex flex-row gap-1">
                                <Fan />
                                Part Cooling
                            </div>
                            <span>{toPercent(controls.partFan.value)}%</span>
                        </div>
                        <Slider
                            onValueChange={(value: number[]) => controls.partFan.onChange(Math.round(value[0]))}
                            onValueCommit={(value: number[]) => controls.partFan.onCommit(Math.round(value[0]))}
                            value={[controls.partFan.value]}
                            max={15}
                            step={1.5}
                            class="w-full"
                        />
                    </div>
                    <div class="bg-400 rounded-lg p-3">
                        <div class="mb-2 flex justify-between">
                            <div class="flex flex-row gap-1">
                                <Fan />
                                Chamber
                            </div>
                            <span>{toPercent(controls.chamberFan.value)}%</span>
                        </div>
                        <Slider
                            onValueChange={(value: number[]) => controls.chamberFan.onChange(Math.round(value[0]))}
                            onValueCommit={(value: number[]) => controls.chamberFan.onCommit(Math.round(value[0]))}
                            value={[controls.chamberFan.value]}
                            max={15}
                            step={1.5}
                            class="w-full"
                        />
                    </div>
                    <div class="bg-400 rounded-lg p-3">
                        <div class="mb-2 flex justify-between">
                            <div class="flex flex-row gap-1">
                                <Fan />
                                Auxillary
                            </div>
                            <span>{toPercent(controls.auxFan.value)}%</span>
                        </div>
                        <Slider
                            onValueChange={(value: number[]) => controls.auxFan.onChange(Math.round(value[0]))}
                            onValueCommit={(value: number[]) => controls.auxFan.onCommit(Math.round(value[0]))}
                            value={[controls.auxFan.value]}
                            max={15}
                            step={1.5}
                            class="w-full"
                        />
                    </div>
                </div>
            </CardContent>
        </Card>
        {#if printerStatus?.ams?.ams_exist_bits === "1"}
            <Card class="space-y-6">
                <CardContent class="p-4">
                    <AmsStatus
                        slots={printerStatus?.ams?.ams?.[0]?.tray?.map((tray) => ({
                            id: tray.id || "",
                            tray_id: tray.tray_id_name || "",
                            material: tray.tray_type || "",
                            k_factor: tray.k?.toFixed(3) || "0.00",
                            color: tray.tray_color || "#808080",
                            active: printerStatus?.ams?.tray_now === tray.id,
                            nozzle_temp_max: tray.nozzle_temp_max || "0",
                            nozzle_temp_min: tray.nozzle_temp_min || "0",
                            tray_temp: tray.tray_temp || "0",
                            tray_sub_brands: tray.tray_sub_brands || "None",
                            tag_uid: tray.tag_uid || "None",
                        })) || []}
                        extSpool={{
                            id: printerStatus.vt_tray?.id || "",
                            tray_id: printerStatus.vt_tray?.tray_id_name || "",
                            material: printerStatus.vt_tray?.tray_type || "",
                            k_factor: printerStatus.vt_tray?.k?.toFixed(3) || "0.00",
                            color: printerStatus.vt_tray?.tray_color || "#808080",
                            active: printerStatus?.ams?.tray_now === printerStatus.vt_tray?.id,
                        }}
                        humidity={printerStatus?.ams?.ams?.[0]?.humidity}
                    />
                </CardContent>
            </Card>
        {/if}
    </div>
</div>
