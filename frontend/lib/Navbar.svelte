<script lang="ts">
    import GitHubButton from "$lib/GitHubButton.svelte";
    import ModeToggleButton from "$lib/ModeToggleButton.svelte";

    import { link } from "@dvcol/svelte-simple-router/router";
    import { getBackendUrl } from "$lib/utils.js";

    import { onMount } from "svelte";
    import bambuiLogo from "../assets/bambui-logo.svg";

    let printers = $state<string[]>([]);
    let currentPage = $state("Dashboard");

    let url = getBackendUrl();

    function updatePageName() {
        const path = window.location.hash.replace("#", "") || window.location.pathname;
        if (path.startsWith("/printer")) {
            currentPage = "Printer";
        } else {
            currentPage = "Dashboard";
        }
    }

    onMount(async () => {
        updatePageName();
        window.addEventListener("hashchange", updatePageName);
        window.addEventListener("popstate", updatePageName);

        try {
            const response = await fetch(url + "/api/printers");
            if (!response.ok) throw new Error("Failed to fetch printers");
            printers = await response.json();
        } catch (error) {
            console.error("Error fetching printers:", error);
        }

        return () => {
            window.removeEventListener("hashchange", updatePageName);
            window.removeEventListener("popstate", updatePageName);
        };
    });
</script>

<div class="sticky top-0 z-50 w-full bg-[#eeeeee] dark:bg-[#28282b]">
        <div class="flex h-[50px] w-full items-center px-4">
        <a href="/" use:link class="flex items-center gap-2" onclick={updatePageName}>
            <img src={bambuiLogo} alt="BambUI" class="h-7 w-7" />
            <span class="text-lg font-semibold text-primary">BambUI</span>
            <span class="text-lg font-light text-primary">&nbsp;|&nbsp;</span>
            <span class="text-lg font-light text-primary">{currentPage}</span>
        </a>

        <div class="ml-auto flex items-center space-x-4">
            <ModeToggleButton />
            <a href="https://github.com/fidoriel/BambUI" target="_blank"> <GitHubButton /></a>
        </div>
    </div>
</div>
