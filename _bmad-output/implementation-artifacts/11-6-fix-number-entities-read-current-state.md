# Story 11.6: Fix Number Entities to Read Current State from Settings

**Status:** ready-for-dev
**Epic:** 11 — Post-Deployment Hardening
**Created:** 2026-05-13

## User Story

As a Sunsynk owner,
I want the number entities (charge/discharge current, generator params, schedule slots) to display their actual current values from the inverter,
So that I can see what's currently configured without having to check the Sunsynk app.

## Problem Statement

All number entities currently return `None` (shown as "Unknown" in HA) because their `native_value` property only returns `self._optimistic_value` which is `None` until the user sets a value. They don't read from `coordinator.data.settings` which already contains the live inverter settings fetched every poll cycle.

## Acceptance Criteria

**Given** the coordinator has fetched settings data successfully
**When** I view any number entity in HA
**Then** it displays the current value from the inverter (not "Unknown")

**Given** I change a value via the HA UI
**When** the write completes and the coordinator refreshes
**Then** the entity shows the confirmed value from the API read-back

**Given** the settings endpoint returns no data for a field
**When** the entity reads its value
**Then** it returns `None` gracefully (not crash)

## Technical Implementation

### Files to Modify

| File | Change |
|------|--------|
| `number/generator.py` | `native_value` reads from `coordinator.data.settings[write_key]` |
| `number/current.py` | `native_value` reads from `coordinator.data.settings["batteryMaxCurrentCharge"]` and `settings["batteryMaxCurrentDischarge"]` |
| `number/schedule.py` | `native_value` reads from `coordinator.data.settings[f"sellTime{slot}Pac"]` and `settings[f"cap{slot}"]` |

### Pattern to Follow

Same pattern used in `select/battery_priority.py` and `select/work_mode.py`:

```python
@property
def native_value(self) -> float | None:
    if self._optimistic_value is not None:
        return self._optimistic_value
    if self.coordinator.data is None:
        return None
    settings = self.coordinator.data.settings
    if not settings:
        return None
    val = settings.get(self._write_key)
    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None
```

### Settings Field Mappings

From the `/api/v1/common/setting/{sn}/read` response:

| Entity | Settings Key |
|--------|-------------|
| Max Charge Current | `batteryMaxCurrentCharge` |
| Max Discharge Current | `batteryMaxCurrentDischarge` |
| Program {N} Power | `sellTime{N}Pac` |
| Program {N} SOC | `cap{N}` |
| Generator Peak-Shaving Power | `genPeakPower` |
| Generator OFF SOC | `genOffCap` |
| Generator ON SOC | `genOnCap` |
| Generator Minimum Solar Power | `genMinSolar` |
| Generator OFF Voltage | `genOffVolt` |
| Generator ON Voltage | `genOnVolt` |
| AC Couple Upper Frequency | `acCoupleFreqUpper` |
| Grid Peak-Shaving Power | `gridPeakPower` |

### Dev Notes

- The `write_key` field already exists on `SunsynkNumberEntityDescription` in generator.py — use it directly
- For current.py, the write key passed to `execute_write` is `charge_current`/`discharge_current` but the settings API field is `batteryMaxCurrentCharge`/`batteryMaxCurrentDischarge` — need to map correctly
- For schedule.py, the write keys are `sellTime{N}Pac` and `cap{N}` — these match the settings response directly
- `coordinator.data.settings` is already populated every poll cycle (added in story 11-2)
- Values in settings come as strings or ints from the API — always cast to float

### Testing

- Verify entities show numeric values after integration loads (not "Unknown")
- Verify changing a value shows optimistic state, then confirmed state after refresh
- Verify entities that don't exist in settings (e.g. genPeakPower on inverters without generator) show None gracefully
