<script lang="ts">
    import { Button } from "$lib/components/ui/button";
    import { Eye, X } from "lucide-svelte";
    import { cn } from "$lib/utils.js";
    import * as Popover from "$lib/components/ui/popover/index.js";

    interface Filament {
        id: string;
        material: string;
        k_factor: string;
        color: string;
        active: boolean;
        nozzle_temp_max: string;
        nozzle_temp_min: string;
        tray_temp: string;
        tray_sub_brands: string;
        tag_uid: string;
    }

    export let slots: Filament[] = [];
    export let extSpool: Filament;

    function formatColor(color: string): string {
        if (!color) return "#808080";
        return color.startsWith("#") ? color : `#${color}`;
    }

    function formatSlotName(id: string): string {
        return "A" + (parseInt(id) + 1).toString();
    }

    // Determine if the filament color is translucent or if material is missing
    function isFilamentTranslucent(filament: Filament): boolean {
        if (filament.tray_sub_brands) {
            return filament.tray_sub_brands.includes("Translucent");
        } else if (!filament.material) {
            return true;
        } else {
            return false;
        }
    }

    // Insert checkerboard classes if filament is translucent
    function tailwindFilamentBoxClass(filament: Filament): string {
        if (isFilamentTranslucent(filament)) {
            return "pattern-rectangles pattern-gray-500 pattern-size-6 pattern-opacity-100"
        } else {
            return ""
        }
    }

    // Computes if a hex color is light or dark and returns the appropriate Tailwind class.
    function tailwindTextColorClass(hex: string): string {
        const cleanColor = hex.replace("#", "");
        if (cleanColor.length < 6) return "text-black";

        const r = parseInt(cleanColor.slice(0, 2), 16);
        const g = parseInt(cleanColor.slice(2, 4), 16);
        const b = parseInt(cleanColor.slice(4, 6), 16);

        const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
        // If the background is light, use black text; otherwise, white text.
        return luminance > 0.5 ? "text-black" : "text-white";
    }
</script>

<div class="bg-400 rounded-lg font-sans">
    <!-- Container holding both the Ext Spool section and AMS section side by side -->
    <div class="flex gap-4 overflow-x-auto">
        <!-- External Spool Section -->
        <div class="flex flex-col flex-none">
          <!-- Row for the “Ext Spool” heading -->
          <div class="text-md flex h-8 items-center gap-2 font-medium">
            <span>Ext Spool</span>
          </div>
    
          <!-- Row holding the spool ID & spool box (similar structure to AMS) -->
          <div class="relative flex gap-2 p-2">
            <div class="flex w-20 flex-col items-center">
              <!-- spool ID row -->
              <div class="text-md flex h-8 items-center text-slate-400">
              </div>
              <!-- spool box -->
              <div
                class={cn('relative flex h-[120px] w-20 flex-col items-center justify-between rounded-lg p-3', tailwindTextColorClass(formatColor(extSpool.color)), tailwindFilamentBoxClass(extSpool))}
                style="background-color: {formatColor(extSpool.color)}"
              >
                {#if extSpool.material}
                  <div class="text-shadow flex flex-col items-center text-sm">
                    <span class="font-medium">{extSpool.material}</span>
                    <span class="text-xs opacity-90">K{extSpool.k_factor}</span>
                  </div>
                  <div class="self-end text-sm">
                    <Eye />
                  </div>
                {:else}
                  <div class="flex flex-col items-center">
                    <span class="text-shadow text-md">?</span>
                  </div>
                {/if}
              </div>
              {#if extSpool.active}
                <span class="relative flex size-3">
                    <span class="absolute inline-flex h-full w-full animate-ping rounded-full bg-green-400 opacity-75"></span>
                    <span class="relative inline-flex size-3 rounded-full bg-green-400"></span>
                </span>
              {/if}
            </div>
          </div>
        </div>

        <!-- AMS Section -->
        <div class="flex-grow">
            <div class="text-md flex h-8 items-center gap-2 font-medium">
                <span>AMS</span>
            </div>

            <div class="relative flex gap-2 p-2">
                {#each slots as slot, index}
                    <div class="flex flex-col w-20 items-center">
                        <div class="text-md flex h-8 items-center text-slate-400">{formatSlotName(slot.id)}</div>
                        <div
                            class={cn('relative flex h-[120px] w-20 flex-col items-center justify-between rounded-lg p-3', tailwindTextColorClass(formatColor(slot.color)), tailwindFilamentBoxClass(slot))}
                            style="background-color: {formatColor(slot.color)}"
                        >
                            {#if slot.material}
                                <div class="text-shadow flex flex-col items-center text-sm">
                                    <span class="font-medium">{slot.material}</span>
                                    <span class="text-xs opacity-90">K{slot.k_factor}</span>
                                </div>
                                <Popover.Root>
                                    <Popover.Trigger>
                                        <Eye />
                                    </Popover.Trigger>
                                    <Popover.Content
                                        class="z-30 w-full max-w-[328px] rounded-[12px] border border-dark-10 bg-background p-4 shadow-popover data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95 data-[side=bottom]:slide-in-from-top-2 data-[side=left]:slide-in-from-right-2 data-[side=right]:slide-in-from-left-2 data-[side=top]:slide-in-from-bottom-2"
                                        sideOffset={8} >
                                            <!-- Filament Info -->
                                            <div class="space-y-2 text-sm">
                                                <div>
                                                    <span class="font-semibold">Filament:</span>
                                                    <span>{slot.material}</span>
                                                </div>
                                                <div>
                                                    <span class="font-semibold">Type:</span>
                                                    <span>{slot.tray_sub_brands}</span>
                                                </div>
                                                <div>
                                                    <span class="font-semibold">Color:</span>
                                                    <span
                                                        class="ml-1 inline-block h-3 w-3 rounded-full border border-gray-400 align-middle"
                                                        style="background-color: {formatColor(slot.color)}"
                                                    ></span>
                                                </div>
                                                <div>
                                                    <span class="font-semibold">Nozzle Temperature:</span>
                                                    <div class="ml-2">
                                                        <span>max: {slot.nozzle_temp_max}°C</span>
                                                        <span class="ml-4">min: {slot.nozzle_temp_min}°C</span>
                                                    </div>
                                                </div>
                                                <div>
                                                    <span class="font-semibold">Serial Number:</span>
                                                    <span>{slot.tag_uid}</span>
                                                </div>

                                                <div class="mt-3 font-semibold">Flow Dynamics</div>
                                                <div class="ml-2">
                                                    <div>
                                                        <span class="font-semibold">Factor K:</span>
                                                        <span>{slot.k_factor}</span>
                                                    </div>
                                                </div>
                                            </div>
                                        </Popover.Content>
                                </Popover.Root>
                            {:else}
                                <div class="flex flex-col items-center">
                                    <span class="text-slate-400">?</span>
                                </div>
                            {/if}
                        </div>
                        {#if slot.active}
                            <span class="relative flex size-3">
                                <span class="absolute inline-flex h-full w-full animate-ping rounded-full bg-green-400 opacity-75"></span>
                                <span class="relative inline-flex size-3 rounded-full bg-green-400"></span>
                            </span>
                        {/if}
                    </div>
                {/each}
            </div>
        </div>
    </div>

    <div class="mt-8 flex gap-3">
        <Button variant="outline" class="w-16" disabled>Unload</Button>
        <Button variant="outline" class="w-16" disabled>Load</Button>
        <Button variant="outline" class="w-16" disabled>Guide</Button>
        <Button variant="outline" class="w-16" disabled>Retry</Button>
    </div>
</div>

<style>
    .text-shadow {
        text-shadow: 0 1px 2px rgba(0, 0, 0, 0.3);
    }
</style>
