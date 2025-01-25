<script lang="ts">
    import { onMount, onDestroy } from "svelte";
    import { useRoute } from "@dvcol/svelte-simple-router/router";
    import { getBackendUrl } from "$lib/utils.js";

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

    import { Label } from "$lib/components/ui/label/index.js";
    import { Switch } from "$lib/components/ui/switch/index.js";
    import { ChevronsLeftRightEllipsis } from "lucide-svelte";

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

    function connect() {
        if (isConnecting) return;
        isConnecting = true;
        const backendUrl = getBackendUrl();
        ws = new WebSocket(`${backendUrl}/ws/printer/${printerId}`);

        ws.onmessage = (event) => {
            reconnectAttempts = 0; // Reset on successful message
            const message = JSON.parse(event.data);
            if (message.type === "jpeg_image") {
                printerSignOfLife = true;
                const binaryData = atob(message.data);
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
                imageSignOfLife = true;
                printerStatus = JSON.parse(message.data) as PrinterStatus;
                printerLightOn = printerStatus?.lights_report?.[0]?.mode === "on";

                printerStatusPulse = true;
                setTimeout(() => (printerStatusPulse = false), 500);
            } else if (message.type === "error") {
                toast(message.data.message);
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

    function toggleLight() {
        ws?.send(
            JSON.stringify({
                type: "chamber_light",
                data: printerStatus?.lights_report?.[0]?.mode === "on" ? false : true,
            }),
        );
    }
    function refreshConnection() {
        ws?.send(
            JSON.stringify({
                type: "force_refresh",
            }),
        );
    }
</script>

<div class="grid grid-flow-row-dense auto-rows-min grid-cols-1 gap-4 p-4 md:grid-cols-5">
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

                    <!-- Print Progress -->
                    <Progress value={printerStatus?.mc_percent || 0} max={100} aria-label="Print progress" />
                </div>
                <div class="mt-4 flex flex-row items-center justify-between space-x-4">
                    <h3 class="text-lg">Status {printerStatus?.print_type} {printerStatus?.mc_percent}%</h3>
                    <Button variant="outline" disabled><CirclePause /></Button>
                    <Button variant="outline" disabled><CircleStop /></Button>
                    <Button variant="outline" disabled><CirclePlay /></Button>
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
                <Button variant="outline" onclick={refreshConnection}><RefreshCw /></Button>
            </div>
        </div>
        <!-- Move Controls (Upper Right) -->
        <Card class="bg-900">
            <CardContent class="p-2">
                <div class="flex flex-col justify-center gap-4 md:flex-row md:gap-8">
                    <!-- XY Controls -->
                    <div class="flex flex-col gap-2">
                        <!-- Y+ Controls -->
                        <div class="flex justify-center">
                            <div class="flex flex-col gap-2">
                                <Button disabled variant="outline" class="w-16">Y+10</Button>
                                <Button disabled variant="outline" class="w-16">Y+1</Button>
                            </div>
                        </div>

                        <!-- X Controls -->
                        <div class="flex gap-2">
                            <Button disabled variant="outline" class="w-16">X-10</Button>
                            <Button disabled variant="outline" class="w-16">X-1</Button>
                            <Button disabled variant="outline" class="w-16">
                                <Home class="h-4 w-4" />
                            </Button>
                            <Button disabled variant="outline" class="w-16">X+1</Button>
                            <Button disabled variant="outline" class="w-16">X+10</Button>
                        </div>

                        <!-- Y- Controls -->
                        <div class="flex justify-center">
                            <div class="flex flex-col gap-2">
                                <Button disabled variant="outline" class="w-16">Y-1</Button>
                                <Button disabled variant="outline" class="w-16">Y-10</Button>
                            </div>
                        </div>
                    </div>

                    <!-- Z and Filament Controls -->
                    <div class="flex gap-8">
                        <!-- Z Controls -->
                        <div class="flex flex-col gap-2">
                            <Button disabled variant="outline" class="w-16">Z+10</Button>
                            <Button disabled variant="outline" class="w-16">Z+1</Button>
                            <Button disabled variant="outline" class="w-16">Z-1</Button>
                            <Button disabled variant="outline" class="w-16">Z-10</Button>
                        </div>

                        <!-- Filament Controls -->
                        <div class="flex flex-col gap-2">
                            <Button disabled variant="outline" class="w-16">Retract</Button>
                            <Button disabled variant="outline" class="w-16">Extrude</Button>
                            <Button disabled variant="outline" class="w-16">Load</Button>
                            <Button disabled variant="outline" class="w-16">Unload</Button>
                        </div>
                    </div>
                </div>
                <div class="mt-6 grid grid-cols-1 gap-4">
                    <div class="bg-400 rounded-lg p-3">
                        <div class="mb-2 flex justify-between">
                            <div class="flex items-center space-x-4">
                                <CircleGauge />
                                Speed
                            </div>
                            <span>Normal</span>
                        </div>
                        <Slider disabled value={[1]} max={3} step={1} class="w-full" />
                    </div>
                </div>
            </CardContent>
        </Card>

        <!-- Chamber Controls (Lower Right) -->
        <Card class="space-y-6">
            <CardContent class="p-4">
                <div class="grid grid-cols-4 gap-4">
                    <div class="flex flex-col items-center justify-center space-y-1">
                        <div class="text-400 flex items-center justify-center space-x-2 text-sm">
                            <Thermometer /> Nozzle
                        </div>
                        <div class="text-center text-xl">
                            {Math.round(printerStatus?.nozzle_temper ?? 0)}/{printerStatus?.nozzle_target_temper}°C
                        </div>
                    </div>
                    <div class="flex flex-col items-center justify-center space-y-1">
                        <div class="text-400 flex items-center justify-center space-x-2 text-sm">
                            <Thermometer /> Bed
                        </div>
                        <div class="text-center text-xl">
                            {Math.round(printerStatus?.bed_temper ?? 0)}/{printerStatus?.bed_target_temper}°C
                        </div>
                    </div>
                    <div class="flex flex-col items-center justify-center space-y-1">
                        <div class="text-400 flex items-center justify-center space-x-2 text-sm">
                            <Thermometer /> Chamber
                        </div>
                        <div class="text-center text-xl">{Math.round(printerStatus?.chamber_temper ?? 0)}°C</div>
                    </div>
                    <div class="flex items-center justify-center space-x-2">
                        <Switch id="printer-light" bind:checked={printerLightOn} onCheckedChange={toggleLight} />
                        <Label for="printer-light">
                            <Lightbulb class="h-5 w-5" />
                        </Label>
                    </div>
                </div>

                <div class="mt-6 grid grid-cols-1 gap-4">
                    <div class="bg-400 rounded-lg p-3">
                        <div class="mb-2 flex justify-between">
                            <div class="flex items-center space-x-4">
                                <Fan />
                                Part Cooling
                            </div>
                            <span>{printerStatus?.cooling_fan_speed}%</span>
                        </div>
                        <Slider disabled value={[42]} max={100} step={5} class="disabled w-full" />
                    </div>
                    <div class="bg-400 rounded-lg p-3">
                        <div class="mb-2 flex justify-between">
                            <div class="flex items-center space-x-4">
                                <Fan />
                                Chamber
                            </div>
                            <span>{printerStatus?.big_fan1_speed}%</span>
                        </div>
                        <Slider disabled value={[42]} max={100} step={5} class="w-full" />
                    </div>
                    <div class="bg-400 rounded-lg p-3">
                        <div class="mb-2 flex justify-between">
                            <div class="flex items-center space-x-4">
                                <Fan />
                                Auxillary
                            </div>
                            <span>{printerStatus?.big_fan2_speed}%</span>
                        </div>
                        <Slider disabled value={[42]} max={100} step={5} class="w-full" />
                    </div>
                </div>
            </CardContent>
        </Card>
    </div>
</div>
