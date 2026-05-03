"""Lovelace dashboard layout definition for Sunsynk."""
from __future__ import annotations


def get_dashboard_config(inverter_sn: str) -> dict:
    """Return the Lovelace dashboard configuration for the given inverter."""
    prefix = f"sunsynk"

    return {
        "title": "Sunsynk Solar",
        "views": [
            {
                "title": "Overview",
                "path": "sunsynk",
                "icon": "mdi:solar-power",
                "cards": [
                    # Power flow card (requires sunsynk-power-flow-card from HACS)
                    {
                        "type": "custom:sunsynk-power-flow-card",
                        "title": "Power Flow",
                        "entities": {
                            "battery": {
                                "entity": f"sensor.{prefix}_battery_soc",
                                "power_entity": f"sensor.{prefix}_battery_power",
                            },
                            "grid": {
                                "entity": f"sensor.{prefix}_grid_power",
                            },
                            "solar": {
                                "entity": f"sensor.{prefix}_pv_power",
                            },
                            "load": {
                                "entity": f"sensor.{prefix}_load_power",
                            },
                        },
                    },
                    # Battery SOC gauge
                    {
                        "type": "gauge",
                        "entity": f"sensor.{prefix}_battery_soc",
                        "name": "Battery SOC",
                        "min": 0,
                        "max": 100,
                        "severity": {
                            "green": 50,
                            "yellow": 20,
                            "red": 0,
                        },
                    },
                    # Energy totals
                    {
                        "type": "entities",
                        "title": "Today's Energy",
                        "entities": [
                            f"sensor.{prefix}_pv_energy_today",
                            f"sensor.{prefix}_grid_import_today",
                            f"sensor.{prefix}_grid_export_today",
                            f"sensor.{prefix}_load_energy_today",
                            f"sensor.{prefix}_battery_charge_today",
                        ],
                    },
                    # Grid & system status
                    {
                        "type": "entities",
                        "title": "System Status",
                        "entities": [
                            f"binary_sensor.{prefix}_grid_connected",
                            f"sensor.{prefix}_system_status",
                            f"sensor.{prefix}_fault_code",
                            f"sensor.{prefix}_weather_temperature",
                            f"sensor.{prefix}_weather_description",
                        ],
                    },
                    # Quick action buttons
                    {
                        "type": "entities",
                        "title": "Controls",
                        "entities": [
                            f"switch.{prefix}_grid_charge",
                            f"select.{prefix}_battery_priority",
                            f"select.{prefix}_work_mode",
                        ],
                    },
                ],
            }
        ],
    }
