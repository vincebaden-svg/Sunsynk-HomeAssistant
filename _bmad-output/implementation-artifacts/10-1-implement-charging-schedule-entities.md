# Story 10.1: Implement Charging Schedule Entities

**Status:** ready-for-dev
**Epic:** 10 — Growth: Advanced Write Surface
**Created:** 2026-05-15

## User Story

As a Sunsynk owner,
I want to configure all 6 charging schedule time slots from HA,
So that I can automate time-of-use charging without using the Sunsynk app.

## Background

The schedule number entities (power + SOC per slot) already exist in `number/schedule.py` and read/write correctly. What's missing are the **time slot** entities (sellTime1–sellTime6) and **enabled** switches (time1on–time6on) that complete the charging schedule control surface.

## Acceptance Criteria

**Given** the integration is running
**When** I view the integration's entities
**Then** for each slot 1–6:
- `select.sunsynk_prog{N}_time` shows the current start time (e.g. "06:00")
- `switch.sunsynk_prog{N}_enabled` shows whether the slot is active
**And** all entities read their current state from `coordinator.data.settings`

**Given** I change a time slot via HA
**When** the write completes
**Then** the API field `sellTime{N}` is updated with the new time string
**And** the entity reflects the confirmed value after read-back

**Given** I toggle a slot enabled switch
**When** the write completes
**Then** the API field `time{N}on` is updated (true/false)
**And** the switch reflects the confirmed state

## Technical Implementation

### Files to Create

| File | Purpose |
|------|---------|
| `select/schedule_time.py` | Select entities for sellTime1–sellTime6 (time picker as select with 30-min options) |
| `switch/schedule_enabled.py` | Switch entities for time1on–time6on |

### Files to Modify

| File | Change |
|------|--------|
| `select/__init__.py` | Register schedule time select entities |
| `switch/__init__.py` | Register schedule enabled switch entities |

### Design Decisions

- **Time as select (not time entity):** HA's `time` platform requires `datetime.time` objects and doesn't map cleanly to the API's "HH:MM" string format. A `select` with 48 options (00:00–23:30 in 30-min increments) is simpler and matches the Sunsynk app's UI.
- **Settings keys:** `sellTime1`–`sellTime6` for times, `time1on`–`time6on` for enabled state
- **Existing entities:** `number/schedule.py` already handles `sellTime{N}Pac` (power) and `cap{N}` (SOC) — those are done

### Settings Field Mappings

| Entity | Settings Key | Format |
|--------|-------------|--------|
| Program {N} Time | `sellTime{N}` | "HH:MM" string |
| Program {N} Enabled | `time{N}on` | true/false boolean |
| Program {N} Power | `sellTime{N}Pac` | numeric (already done) |
| Program {N} SOC | `cap{N}` | numeric (already done) |

### Valid Time Options

```python
TIME_OPTIONS = [
    "00:00", "00:30", "01:00", "01:30", "02:00", "02:30",
    "03:00", "03:30", "04:00", "04:30", "05:00", "05:30",
    "06:00", "06:30", "07:00", "07:30", "08:00", "08:30",
    "09:00", "09:30", "10:00", "10:30", "11:00", "11:30",
    "12:00", "12:30", "13:00", "13:30", "14:00", "14:30",
    "15:00", "15:30", "16:00", "16:30", "17:00", "17:30",
    "18:00", "18:30", "19:00", "19:30", "20:00", "20:30",
    "21:00", "21:30", "22:00", "22:30", "23:00", "23:30",
]
```

### Dev Notes

- Write key for time: pass `sellTime{N}` directly (already in WRITE_TIERS as Tier 2)
- Write key for enabled: pass `time{N}on` directly (already in WRITE_TIERS as Tier 2)
- The `write_setting` method handles `time{N}on` as a boolean field (sends true/false)
- The `write_setting` method handles `sellTime{N}` as a string (passes through as-is)
- Read from `coordinator.data.settings["sellTime{N}"]` and `settings["time{N}on"]`
- Pattern: same as battery_priority select and grid_charge switch
