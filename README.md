# BambUI

> <span style="color:red;">This software is in a very early stage of development. Please note the liability clause of the AGPL license you agree to when using this program.</span>

A simple and slim UI for LAN mode of Bambu Lab Printers.
I do not trust Bambu Cloud and wanted an easy way to access my Printer P1S via home VPN.
I also do not like their Network Plugin for print monitoring, all current solutions including Home Assistant did not fit my needs, so I decided to build my own.
Currently, only P1S printers are supported. The UI shows a lot of buttons, but all disabled ones are not implemented yet.

Features:

- Add as many printers as you like
- Camera Stream
- UI control
- No Cloud required (works only in Lan Mode)
- Mobile friendly
- svelte, shadcn/ui, FastApi and docker (with vite and poetry)
- Connections running via server, so printer CPU is not overutilized
- Connect as many Clients as you want
- ready to use docker image (see `docker-compose.yaml`)

## Installation

The following printer models are supported:

- P1 Series P1S and P1P
- A1 Series A1 and A1M

You will need 4 Env vars to add a printer:

For the printer model following strings are used: `P1S`, `P1P`, `A1` or `A1M`.

Replace `<something>` with the apropiate values for your machine.
You may add as many printers as you like.
`<PRINTER_NAME>` is an arbitrary name you give your machine.
You may use it for identification.
All env vars associated with one printer may have the same name.
This name will be visible across the UI.
You may choose this at any time.
It has no functionality except identification and is no referral to the printer, so you may choose a name that you like.
It will only be used within BambUI.
You can add this env block for as many printers as you like.

```bash
BAMBUI_PRINTER.<PRINTER_NAME>.IP=<PRINTER_IP>
BAMBUI_PRINTER.<PRINTER_NAME>.ACCESS_CODE=<PRINTER_ACCESS_CODE>
BAMBUI_PRINTER.<PRINTER_NAME>.SERIAL=<PRINTER_SERIAL_NUMBER>
BAMBUI_PRINTER.<PRINTER_NAME>.MODEL=<PRINTER_MODEL>
```

### Using docker commandline

Start the service:

```bash
docker run \
  -p 8080:8080  \
  --restart always \
  -e BAMBUI_PRINTER.MY-P1S.IP=192.168.12.42 \
  -e BAMBUI_PRINTER.MY-P1S.ACCESS_CODE=12345678 \
  -e BAMBUI_PRINTER.MY-P1S.SERIAL=01P00C12345678 \
  -e BAMBUI_PRINTER.MY-P1S.MODEL=P1S \
  ghcr.io/fidoriel/bambui:edge
```

### Using docker compose

Write a compose file as bambui.yml:

```yaml
services:
    bambui:
        image: ghcr.io/fidoriel/bambui:edge
        restart: always
        ports:
            - 8080:8080
        environment:
            - BAMBUI_PRINTER.MY-P1S.IP=192.168.12.42
            - BAMBUI_PRINTER.MY-P1S.ACCESS_CODE=12345678
            - BAMBUI_PRINTER.MY-P1S.SERIAL=01P00C12345678
            - BAMBUI_PRINTER.MY-P1S.MODEL=P1S
```

Start the service in the background (-d):

```bash
docker compose -f bambui.yml up -d
```

### Using a Portainer stack

  - Login to Portainer
  - Go to "Stacks"
  - Click "Add stack"
  - Enter the name "Bambui"
  - Paste the content of the bambui.yml file from "Using docker compose" into the "Web editor"
  - Click "Deploy the stack"

## Development

Create an `.env` based on `.env.example`
Set Up:

```bash
poetry install
uvicorn backend.main:app --port 8000 --env-file .env --reload
npm i
npm run dev
```

Lint

```bash
mypy .
ruff check .
ruff format .
npm run format
npm run build
```
