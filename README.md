# ha-sunsynk

A Home Assistant custom integration for Sunsynk solar inverters.

## Overview

The Sunsynk HA integration transforms a Sunsynk solar inverter from a passively monitored device into an active participant in home energy management. It exposes inverter data as Home Assistant entities and provides automation blueprints for common energy management scenarios.

## Features

- Real-time monitoring of PV power, battery SOC, grid import/export, and load power
- Grid failure/restore events for automation triggers
- Battery SOC and solar generation threshold alerts
- Write services for inverter control (battery priority, grid charge, work mode)
- Pre-installed automation blueprints (no YAML required)
- Auto-provisioned Lovelace dashboard
- Dual API support: Official OpenAPI and Unofficial Connect API

## Installation

Install via [HACS](https://hacs.xyz/) by adding this repository as a custom integration.

## Requirements

- Home Assistant 2024.1.0 or later
- Sunsynk inverter with WiFi Logger v2
- Sunsynk Connect account credentials

## Configuration

After installation, add the integration via **Settings → Devices & Services → Add Integration → Sunsynk Solar Inverter**.

## Documentation

- [Telegram Setup](docs/telegram_setup.md)
- [Email Setup](docs/email_setup.md)
- [Official API Setup](docs/official_api_setup.md)

## Docker

The integration ships with a multi-stage `Dockerfile` targeting **armv7** (Raspberry Pi 3B) with a memory footprint ≤150 MB RSS.

```bash
# Build for armv7 (default)
docker build -t ha-sunsynk .

# Override base image for a different architecture (e.g. aarch64)
docker build \
  --build-arg BUILD_FROM=ghcr.io/home-assistant/aarch64-base-python:3.12 \
  -t ha-sunsynk .
```

The build uses a two-stage process: a builder stage installs `gcc`, `libffi-dev`, and `openssl-dev` to compile the `cryptography` package's C extensions, then copies only the compiled wheels into the lean final image.

## License

MIT
