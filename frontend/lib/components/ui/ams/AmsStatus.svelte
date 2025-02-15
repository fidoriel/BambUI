<script lang="ts">
    import { Button } from "$lib/components/ui/button";

    interface AmsSlot {
        id: string;
        material: string;
        k_factor: string;
        color: string;
        active: boolean;
    }

    export let slots: AmsSlot[] = [];
    export let activeSlot: number = 0;
    export let extruderConnected: boolean = false;

    function formatColor(color: string): string {
        if (!color) return '#808080';
        return color.startsWith('#') ? color : `#${color}`;
    }
</script>

<div class="rounded-lg bg-400 text-white font-sans">
    <div class="flex items-start gap-8">
        <!-- External Spool Section -->
        <div class="flex flex-col items-center">
            <!-- 1. “Ext Spool” label row -->
            <div class="h-8 flex items-center gap-2 text-sm">
            <span>Ext Spool</span>
            </div>
            <!-- 2. Extra row to match the AMS spool ID row -->
            <div class="h-8 flex items-center text-sm text-slate-400">
            <!-- blank or something like "EXT" if you prefer -->
            </div>
            <!-- 3. Spool box itself -->
            <div
            class="w-20 h-[120px] border-2 border-dashed border-slate-600
                rounded-lg flex items-center justify-center bg-transparent"
            >
            <span class="text-slate-400">?</span>
            </div>
        </div>

        <!-- AMS Section -->
        <div class="flex-grow">
            <div class="h-8 flex items-center gap-2 text-sm">
                <span>AMS</span>
            </div>
            
            <div class="flex gap-4 relative">
                {#each slots as slot, index}
                <div class="flex flex-col items-center">
                    <div class="h-8 flex items-center text-sm text-slate-400">{slot.id}</div>
                    <div 
                        class="w-20 h-[120px] rounded-lg p-3 flex flex-col justify-between relative"
                        style="background-color: {formatColor(slot.color)}"
                    >
                        <div class="flex flex-col items-center text-white text-shadow text-sm">
                            <span class="font-medium">{slot.material}</span>
                            <span class="text-xs opacity-90">K{slot.k_factor}</span>
                        </div>
                        <div class="self-end text-sm">👁️</div>
                    </div>
                    {#if slot.active}
                        <div class="absolute -bottom-10 w-full flex flex-col items-center">
                            <div class="w-0.5 h-5 bg-slate-600"></div>
                            <div class="w-5 h-5 rounded-full bg-slate-700 flex items-center justify-center -mt-px">
                                <div 
                                    class="w-2.5 h-2.5 rounded-full"
                                    style="background-color: {formatColor(slot.color)}"
                                ></div>
                            </div>
                        </div>
                    {/if}
                </div>
            {/each}
        </div>
    </div>
</div>

<div class="flex gap-3 mt-8">
    <Button variant="outline" class="w-16" disabled>
        Unload
    </Button>
    <Button variant="outline" class="w-16" disabled>
        Load
    </Button>
    <Button variant="outline" class="w-16" disabled>
        Guide
    </Button>
    <Button variant="outline" class="w-16" disabled>
        Retry
    </Button>
</div>
</div>

<style>
.text-shadow {
    text-shadow: 0 1px 2px rgba(0,0,0,0.3);
}
</style>