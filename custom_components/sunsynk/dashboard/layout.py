"""Lovelace dashboard layout definition for Sunsynk."""
from __future__ import annotations


def get_dashboard_config(inverter_sn: str) -> dict:
    """Return the Lovelace dashboard configuration for the given inverter.

    Uses only built-in HA cards so no HACS dependencies are required.
    If the user has sunsynk-power-flow-card installed, they can swap in
    the custom card manually.
    """
    prefix = "sunsynk"

    return {
        "title": "Sunsynk Solar",
        "views": [
            {
                "title": "Overview",
                "path": "sunsynk-overview",
                "icon": "mdi:solar-power",
                "type": "sections",
                "sections": [
                    {
                        "type": "grid",
                        "cards": [
                            # PV Power
                            {
                                "type": "tile",
                                "entity": f"sensor.{prefix}_pv_power",
                                "name": "Solar",
                                "icon": "mdi:solar-panel-large",
                                "color": "amber",
                            },
                            # Battery Power
                            {
                                "type": "tile",
                                "entity": f"sensor.{prefix}_battery_power",
                                "name": "Battery",
                                "icon": "mdi:battery-charging",
                                "color": "green",
                            },
                            # Grid Power
                            {
                                "type": "tile",
                                "entity": f"sensor.{prefix}_grid_power",
                                "name": "Grid",
                                "icon": "mdi:transmission-tower",
                                "color": "red",
                            },
                            # Load Power
                            {
                                "type": "tile",
                                "entity": f"sensor.{prefix}_load_power",
                                "name": "Load",
                                "icon": "mdi:home-lightning-bolt",
                                "color": "blue",
                            },
                        ],
                    },
                    {
                        "type": "grid",
                        "cards": [
                            # Battery SOC gauge
                            {
                                "type": "gauge",
                                "entity": f"sensor.{prefix}_battery_soc",
                                "name": "Battery",
                                "unit": "%",
                                "min": 0,
                                "max": 100,
                                "severity": {
                                    "green": 50,
                                    "yellow": 20,
                                    "red": 0,
                                },
                                "needle": True,
                            },
                            # Grid connected
                            {
                                "type": "tile",
                                "entity": f"binary_sensor.{prefix}_grid_connected",
                                "name": "Grid Status",
                                "icon": "mdi:transmission-tower",
                            },
                        ],
                    },
                ],
            },
            {
                "title": "Energy",
                "path": "sunsynk-energy",
                "icon": "mdi:lightning-bolt",
                "cards": [
                    # Today's energy
                    {
                        "type": "entities",
                        "title": "Today's Energy (kWh)",
                        "entities": [
                            {
                                "entity": f"sensor.{prefix}_pv_energy_today",
                                "name": "Solar Generated",
                                "icon": "mdi:solar-power",
                            },
                            {
                                "entity": f"sensor.{prefix}_battery_charge_today",
                                "name": "Battery Charged",
                                "icon": "mdi:battery-plus",
                            },
                            {
                                "entity": f"sensor.{prefix}_battery_discharge_today",
                                "name": "Battery Discharged",
                                "icon": "mdi:battery-minus",
                            },
                            {
                                "entity": f"sensor.{prefix}_grid_import_today",
                                "name": "Grid Import",
                                "icon": "mdi:transmission-tower-import",
                            },
                            {
                                "entity": f"sensor.{prefix}_grid_export_today",
                                "name": "Grid Export",
                                "icon": "mdi:transmission-tower-export",
                            },
                            {
                                "entity": f"sensor.{prefix}_load_energy_today",
                                "name": "Load Consumed",
                                "icon": "mdi:home-lightning-bolt",
                            },
                        ],
                    },
                    # History graph
                    {
                        "type": "history-graph",
                        "title": "Power (last 24h)",
                        "hours_to_show": 24,
                        "entities": [
                            {"entity": f"sensor.{prefix}_pv_power", "name": "Solar"},
                            {"entity": f"sensor.{prefix}_battery_power", "name": "Battery"},
                            {"entity": f"sensor.{prefix}_grid_power", "name": "Grid"},
                            {"entity": f"sensor.{prefix}_load_power", "name": "Load"},
                        ],
                    },
                ],
            },
            {
                "title": "Controls",
                "path": "sunsynk-controls",
                "icon": "mdi:tune",
                "cards": [
                    {
                        "type": "entities",
                        "title": "Inverter Controls",
                        "entities": [
                            {
                                "entity": f"select.{prefix}_work_mode",
                                "name": "Work Mode",
                            },
                            {
                                "entity": f"switch.{prefix}_grid_charge",
                                "name": "Grid Charge",
                            },
                        ],
                    },
                ],
            },
        ],
    }
