# Sunsynk Solar Inverter — Home Assistant Integration

A full-featured Home Assistant custom integration for Sunsynk hybrid inverters. Monitor real-time power flows, battery state, and energy totals — and control charging schedules, work modes, and generator settings directly from your HA dashboard.

## Who Is This For?

Owners of Sunsynk (or Deye/Turbo-Energy rebrand) hybrid inverters who want:

- Real-time solar, battery, grid, and load monitoring in Home Assistant
- Control over charging schedules without opening the Sunsynk app
- Automations triggered by grid failures, low battery, or solar conditions
- Telegram notifications for daily summaries and critical events
- A pre-built dashboard with power flow visualization

---

## Features

- **Real-time power sensors** — PV, battery, grid, load (W)
- **Energy totals** — daily, monthly, yearly (kWh) compatible with HA Energy Dashboard
- **Battery state** — SOC, voltage, current, temperature, capacity
- **Grid connection monitoring** — binary sensor + event firing on failure/restore
- **Inverter controls** — work mode, battery priority, grid charge, charge/discharge current limits
- **6-slot charging schedule** — time, power, SOC, grid charge, gen charge per slot
- **Generator controls** — peak-shaving power, on/off SOC, on/off voltage, min solar
- **Auto-provisioned dashboard** — 3 views (Overview, Controls, Timer) created on first setup
- **5 automation blueprints** — grid failure, low battery, daily summary, summer load priority, pool motor control
- **Telegram notifications** — via bundled blueprints
- **Configurable PV strings** — 1 to 4 MPPT inputs
- **Safety tiers** — write operations are logged (Tier 2) or require confirmation (Tier 3)
- **Local time-series storage** — SQLite database with configurable retention

---

## Requirements

| Requirement | Details |
|---|---|
| Home Assistant | 2024.1.0 or newer (tested on 2026.5) |
| HACS | Required for easy installation |
| Sunsynk Account | Registered at [sunsynk.net](https://www.sunsynk.net) |
| API Credentials | App Key + App Secret from the Sunsynk developer portal (official mode) **or** username + password (unofficial mode) |
| Inverter | Any Sunsynk/Deye hybrid inverter with cloud connectivity |

---

## Installation

### Via HACS (Recommended)

1. Open HACS in Home Assistant
2. Click the three-dot menu → **Custom repositories**
3. Add repository URL: `https://github.com/vincebaden-svg/Sunsynk-HomeAssistant`
4. Category: **Integration**
5. Click **Add**, then find "Sunsynk Solar Inverter" in the HACS store
6. Click **Download**
7. Restart Home Assistant

### Manual Installation

1. Download or clone this repository
2. Copy the `custom_components/sunsynk` folder into your HA `config/custom_components/` directory
3. Restart Home Assistant

---

## Configuration

### Config Flow

After installation, add the integration via the UI:

1. Go to **Settings → Devices & Services → Add Integration**
2. Search for **Sunsynk Solar Inverter**

#### Step 1: Choose API Mode

| Mode | Description |
|---|---|
| **Official** | Uses HMAC-authenticated official API (`openapi.sunsynk.net`). Requires App Key + App Secret + username + password. More reliable. |
| **Unofficial** | Uses bearer-token API (`api.sunsynk.net`). Only requires username + password. May be blocked by Cloudflare on newer accounts. |

> **Note:** The official mode uses a hybrid approach — HMAC auth against the official endpoint, then fetches detailed data from the unofficial API using the obtained token.

#### Step 2: Enter Credentials

**Official mode:**
- App Key (from Sunsynk developer portal)
- App Secret
- Username (Sunsynk account email)
- Password

**Unofficial mode:**
- Username
- Password
- Region: `api.sunsynk.net` (default) or `pv.inteless.com`

#### Step 3: Inverter Serial Number

Enter your inverter serial number (found on the inverter label or in the Sunsynk app under Plant → Inverter).

### Options (After Setup)

Go to the integration entry → **Configure** to adjust:

| Option | Default | Range | Description |
|---|---|---|---|
| Poll Interval | 5 min | 1–60 min | How often to fetch data from the API |
| PV Strings | 2 | 1–4 | Number of MPPT/PV string sensors to create |
| SOC Threshold | 20% | 0–100% | Battery low threshold for events |
| Solar Threshold | 500 W | 0–20000 W | Minimum PV for solar-related automations |
| Summary Time | 18:00 | HH:MM | When to fire the daily summary event |
| Retention Days | 30 | 1–365 | Days to keep local time-series data |

---

## Entities

### Sensors — Power (W)

| Entity ID | Name | Description |
|---|---|---|
| `sensor.sunsynk_pv_power` | PV Power | Total solar generation |
| `sensor.sunsynk_pv1_power` | PV1 Power | String 1 power (if configured) |
| `sensor.sunsynk_pv2_power` | PV2 Power | String 2 power (if configured) |
| `sensor.sunsynk_pv3_power` | PV3 Power | String 3 power (if configured) |
| `sensor.sunsynk_pv4_power` | PV4 Power | String 4 power (if configured) |
| `sensor.sunsynk_battery_power` | Battery Power | Positive = charging, negative = discharging |
| `sensor.sunsynk_grid_power` | Grid Power | Positive = importing, negative = exporting |
| `sensor.sunsynk_load_power` | Load Power | Total household consumption |

### Sensors — Battery State

| Entity ID | Name | Unit |
|---|---|---|
| `sensor.sunsynk_battery_soc` | Battery SOC | % |
| `sensor.sunsynk_battery_voltage` | Battery Voltage | V |
| `sensor.sunsynk_battery_current` | Battery Current | A |
| `sensor.sunsynk_battery_temp` | Battery Temperature | °C |
| `sensor.sunsynk_battery_capacity` | Battery Capacity | Ah |

### Sensors — Energy (kWh)

| Entity ID | Name | Period |
|---|---|---|
| `sensor.sunsynk_pv_energy_today` | PV Energy Today | Daily |
| `sensor.sunsynk_battery_charge_today` | Battery Charge Today | Daily |
| `sensor.sunsynk_battery_discharge_today` | Battery Discharge Today | Daily |
| `sensor.sunsynk_grid_import_today` | Grid Import Today | Daily |
| `sensor.sunsynk_grid_export_today` | Grid Export Today | Daily |
| `sensor.sunsynk_load_energy_today` | Load Energy Today | Daily |
| `sensor.sunsynk_pv_energy_month` | PV Energy Month | Monthly |
| `sensor.sunsynk_grid_import_month` | Grid Import Month | Monthly |
| `sensor.sunsynk_load_energy_month` | Load Energy Month | Monthly |
| `sensor.sunsynk_pv_energy_year` | PV Energy Year | Yearly |
| `sensor.sunsynk_grid_import_year` | Grid Import Year | Yearly |
| `sensor.sunsynk_load_energy_year` | Load Energy Year | Yearly |

All energy sensors use `state_class: total_increasing` and are compatible with the HA Energy Dashboard.

### Binary Sensors

| Entity ID | Name | Description |
|---|---|---|
| `binary_sensor.sunsynk_grid_connected` | Grid Connected | ON when grid is available. Fires `sunsynk_grid_failure` / `sunsynk_grid_restored` events on state change. |

### Switches

| Entity ID | Name | Description |
|---|---|---|
| `switch.sunsynk_grid_charge` | Grid Charge | Enable/disable grid charging globally |
| `switch.sunsynk_use_timer` | Use Timer | Enable/disable the 6-slot timer system |
| `switch.sunsynk_program_1_grid_charge` | Program 1 Grid Charge | Grid charge for time slot 1 |
| `switch.sunsynk_program_1_gen_charge` | Program 1 Gen Charge | Generator charge for time slot 1 |
| … | Programs 2–6 | Same pattern for slots 2 through 6 |

### Selects

| Entity ID | Name | Options |
|---|---|---|
| `select.sunsynk_work_mode` | Work Mode | `self_use`, `time_of_use`, `backup`, `peak_shaving` |
| `select.sunsynk_battery_priority` | Battery Priority | `battery`, `load` |
| `select.sunsynk_program_1_time` | Program 1 Time | `00:00` to `23:30` (30-min increments) |
| … | Programs 2–6 Time | Same pattern for slots 2 through 6 |

### Numbers — Battery Current Limits

| Entity ID | Name | Unit | Range |
|---|---|---|---|
| `number.sunsynk_charge_current` | Max Charge Current | A | 0–185 |
| `number.sunsynk_discharge_current` | Max Discharge Current | A | 0–185 |

### Numbers — Schedule (per slot, 6 slots)

| Entity ID Pattern | Name | Unit | Range |
|---|---|---|---|
| `number.sunsynk_program_N_power` | Program N Power | W | 0–8000 |
| `number.sunsynk_program_N_soc` | Program N SOC | % | 0–100 |

### Numbers — Generator & Grid

| Entity ID | Name | Unit | Range |
|---|---|---|---|
| `number.sunsynk_gen_peak_power` | Generator Peak-Shaving Power | W | 500–30000 |
| `number.sunsynk_gen_off_cap` | Generator OFF SOC | % | 0–100 |
| `number.sunsynk_gen_on_cap` | Generator ON SOC | % | 0–100 |
| `number.sunsynk_gen_min_solar` | Generator Minimum Solar Power | W | 0–10000 |
| `number.sunsynk_gen_off_volt` | Generator OFF Voltage | V | 40–60 |
| `number.sunsynk_gen_on_volt` | Generator ON Voltage | V | 40–60 |
| `number.sunsynk_ac_couple_freq_upper` | AC Couple Upper Frequency | Hz | 50–65 |
| `number.sunsynk_grid_peak_power` | Grid Peak-Shaving Power | W | 0–30000 |

---

## Dashboard

### Auto-Provisioned Dashboard

On first setup, the integration creates a **Sunsynk Solar** dashboard with three views:

1. **Overview** — Battery gauge, today's energy summary, system status
2. **Controls** — Work mode, battery priority, grid charge, PV strings, 24h history graph
3. **Timer** — Full 6-slot schedule grid (see Timer/Schedule section below)

The dashboard appears in your sidebar automatically. You can customize it freely — the integration won't overwrite your changes.

### Power Flow Card (Optional)

For an animated power flow visualization similar to the Sunsynk Connect app:

1. Install `sunsynk-power-flow-card` from HACS → Frontend
2. Restart HA
3. Edit the Sunsynk Solar dashboard → Raw configuration editor
4. Paste the configuration from [`docs/powerflow-card-setup.md`](docs/powerflow-card-setup.md)

Key settings to adjust:
- `mppts: 2` — change to match your PV string count
- `battery.energy: 0` — set to total battery Wh for runtime estimates (e.g. `15960` for 3× 5.32 kWh)
- `battery.shutdown_soc: 20` — match your actual shutdown SOC

---

## Timer / Schedule

The integration exposes the inverter's 6-slot charging schedule as individual entities, giving you full control from HA.

### How It Works

Each of the 6 time slots has:
- **Time** (select) — when the slot starts (00:00–23:30 in 30-min steps)
- **Power** (number) — charge power limit in watts (0–8000 W)
- **SOC** (number) — target battery SOC for this slot (0–100%)
- **Grid Charge** (switch) — whether to charge from grid during this slot
- **Gen Charge** (switch) — whether to charge from generator during this slot

The global **Use Timer** switch enables or disables the entire schedule system.

### Timer Dashboard Card

The auto-provisioned Timer view displays all 6 slots in a grid layout. You can also add it manually to any dashboard using the YAML in [`docs/timer-card.yaml`](docs/timer-card.yaml):

```yaml
type: vertical-stack
cards:
  - type: entities
    title: System Mode Timer
    entities:
      - entity: switch.sunsynk_use_timer
        name: Use Timer
  - type: grid
    columns: 5
    square: false
    cards:
      # Each row: Time | Power | SOC | Grid | Gen
      - type: tile
        entity: select.sunsynk_program_1_time
      - type: tile
        entity: number.sunsynk_program_1_power
      # ... (see docs/timer-card.yaml for full config)
```

### Example: Off-Peak Charging

To charge from the grid during off-peak hours (00:00–05:00) up to 80% SOC at 3000 W:

1. Turn on **Use Timer** (`switch.sunsynk_use_timer`)
2. Set **Program 1 Time** to `00:00`
3. Set **Program 1 Power** to `3000`
4. Set **Program 1 SOC** to `80`
5. Turn on **Program 1 Grid Charge**
6. Set **Program 2 Time** to `05:00` (marks end of slot 1)

---

## Blueprints

The integration auto-installs 5 automation blueprints to `/config/blueprints/automation/sunsynk/` on first setup.

### Available Blueprints

| Blueprint | Description | Inputs |
|---|---|---|
| **Grid Failure Notification** | Telegram alert when grid fails or restores, includes battery SOC | Telegram Chat ID |
| **Low Battery Alert** | Telegram alert when battery drops below configured threshold | Telegram Chat ID |
| **Daily Energy Summary** | Daily Telegram message with solar/grid/load/battery stats | Telegram Chat ID |
| **Summer Load Priority** | Auto-switches to load priority when solar is high + battery full | PV threshold, SOC threshold, time window |
| **Pool Motor SOC Control** | Turns off a switch when SOC drops or grid fails, restores when recovered | Switch entity, SOC off/on thresholds |

### Setting Up a Blueprint

1. Go to **Settings → Automations & Scenes → Blueprints**
2. Find the Sunsynk blueprint you want
3. Click **Create Automation**
4. Fill in the inputs (e.g., Telegram Chat ID)
5. Save

### Telegram Setup

The Grid Failure, Low Battery, and Daily Summary blueprints send notifications via Telegram. See [`docs/telegram_setup.md`](docs/telegram_setup.md) for full setup instructions, summarized here:

1. Create a bot via **@BotFather** in Telegram
2. Get your Chat ID by messaging the bot and checking `https://api.telegram.org/botYOUR_TOKEN/getUpdates`
3. Add the **Telegram Bot** integration in HA (Settings → Devices & Services → Add Integration → Telegram Bot → Polling)
4. Enter your bot token and chat ID
5. Use the resulting `notify` entity or chat ID in the blueprint inputs

### Custom Events

The integration fires these events that blueprints (and your own automations) can trigger on:

| Event | Fired When | Data |
|---|---|---|
| `sunsynk_grid_failure` | Grid connection lost | `inverter_sn`, `battery_soc`, `timestamp` |
| `sunsynk_grid_restored` | Grid connection restored | `inverter_sn`, `battery_soc`, `timestamp` |
| `sunsynk_battery_low` | SOC drops below threshold | `soc`, `threshold` |
| `sunsynk_daily_summary` | At configured summary time | `date`, `pv_energy_today`, `grid_import_today`, `grid_export_today`, `load_energy_today`, `battery_charge_today`, `battery_discharge_today` |

---

## Troubleshooting

### Cannot Connect During Setup

- **Official mode:** Verify your App Key and App Secret are correct. These come from the Sunsynk developer portal, not the mobile app.
- **Unofficial mode:** Newer Sunsynk accounts may be blocked by Cloudflare bot protection. Try official mode instead.
- Check that your inverter serial number is correct (found on the physical inverter label or in the Sunsynk app).

### Entities Show "Unavailable"

- The API may be temporarily unreachable. Check your internet connection.
- Verify the inverter is online in the Sunsynk Connect app.
- Check HA logs: **Settings → System → Logs**, filter for `sunsynk`.
- If the issue persists after a restart, try reconfiguring credentials (integration menu → three dots → Reconfigure).

### Stale Data / Not Updating

- Default poll interval is 5 minutes. Reduce it in Options if needed (minimum 1 minute).
- The Sunsynk cloud API itself updates every ~5 minutes from the inverter's WiFi dongle.
- Check that the dongle has a solid connection (green LED on the dongle).

### Write Operations Fail

- Write operations use safety tiers. Tier 2 operations are logged; Tier 3 operations require confirmation.
- Check HA logs for specific error messages from the API.
- Some settings may not be writable depending on your inverter firmware version.

### Dashboard Not Appearing

- The dashboard is provisioned on first setup. If you removed it, delete and re-add the integration to trigger re-provisioning.
- Check **Settings → Dashboards** to see if "Sunsynk Solar" exists but is hidden.

### Blueprints Not Showing

- Blueprints are copied to `/config/blueprints/automation/sunsynk/` on integration setup.
- If missing, restart HA — they'll be installed on next load.
- Check file permissions if running HA in Docker.

### Telegram Notifications Not Working

- Ensure you've sent at least one message to your bot before adding the integration.
- Verify the chat ID is numeric (not the bot username).
- Check that the Telegram Bot integration is set up with **Polling** mode (not webhook, which requires external access).
- See [`docs/telegram_setup.md`](docs/telegram_setup.md) for detailed steps.

### Energy Dashboard Not Tracking

- Energy sensors use `state_class: total_increasing` and should appear automatically in **Settings → Dashboards → Energy**.
- If sensors don't appear in the energy config, wait for at least one poll cycle after setup.
- Ensure the sensors have non-null values (check Developer Tools → States).

---

## Safety & Write Tiers

Write operations to the inverter are categorized by risk:

| Tier | Examples | Behavior |
|---|---|---|
| Tier 1 (Read) | All sensors, binary sensors | No restrictions |
| Tier 2 (Logged Write) | Work mode, battery priority, schedule changes | Logged to HA system log |
| Tier 3 (Confirmed Write) | Charge/discharge current limits, generator settings | Requires explicit confirmation |

---

## Project Info

- **Version:** 0.1.0
- **Domain:** `sunsynk`
- **IoT Class:** Cloud Polling
- **Codeowners:** [@vincebaden-svg](https://github.com/vincebaden-svg)
- **Repository:** [github.com/vincebaden-svg/Sunsynk-HomeAssistant](https://github.com/vincebaden-svg/Sunsynk-HomeAssistant)

---

## License

See [LICENSE](LICENSE) for details.
