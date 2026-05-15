"""Shared credential loader for test scripts.

Loads credentials from (in priority order):
1. Environment variables (SUNSYNK_APP_KEY, SUNSYNK_APP_SECRET, etc.)
2. Config file: test_config.json (gitignored)
3. Interactive prompts

Usage:
    from test_credentials import load_credentials
    creds = load_credentials()
    # creds["app_key"], creds["app_secret"], creds["username"], creds["password"], creds["inverter_sn"]
"""
import getpass
import json
import os
from pathlib import Path

CONFIG_FILE = Path(__file__).parent / "test_config.json"


def load_credentials() -> dict:
    """Load credentials from env vars, config file, or prompts."""
    creds = {
        "app_key": os.environ.get("SUNSYNK_APP_KEY", ""),
        "app_secret": os.environ.get("SUNSYNK_APP_SECRET", ""),
        "username": os.environ.get("SUNSYNK_USERNAME", ""),
        "password": os.environ.get("SUNSYNK_PASSWORD", ""),
        "inverter_sn": os.environ.get("SUNSYNK_INVERTER_SN", ""),
    }

    # Try config file if any value is missing
    if not all(creds.values()) and CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE) as f:
                file_creds = json.load(f)
            for key in creds:
                if not creds[key] and key in file_creds:
                    creds[key] = file_creds[key]
        except (json.JSONDecodeError, OSError):
            pass

    # Prompt for any still-missing values
    if not creds["app_key"]:
        creds["app_key"] = input("App Key: ")
    if not creds["app_secret"]:
        creds["app_secret"] = getpass.getpass("App Secret: ")
    if not creds["username"]:
        creds["username"] = input("Username (email): ")
    if not creds["password"]:
        creds["password"] = getpass.getpass("Password: ")
    if not creds["inverter_sn"]:
        creds["inverter_sn"] = input("Inverter Serial Number: ")

    return creds
