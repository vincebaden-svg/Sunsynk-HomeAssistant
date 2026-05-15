#!/usr/bin/env python3
"""Read all sensor data from every Sunsynk API endpoint and display values.

Credentials loaded from test_config.json, env vars, or interactive prompts.
"""
import base64
import hashlib
import hmac
import json
import uuid

import requests

from test_credentials import load_credentials

OFFICIAL_API_BASE = "https://openapi.sunsynk.net"
UNOFFICIAL_API_BASE = "https://api.sunsynk.net"


def compute_md5(data): return base64.b64encode(hashlib.md5(data.encode()).digest()).decode()
def compute_hmac(text, secret): return base64.b64encode(hmac.new(secret.encode(), text.encode(), hashlib.sha256).digest()).decode()


def get_data(url, headers, label):
    resp = requests.get(url, headers=headers)
    if resp.status_code != 200:
        print(f"  [{label}] FAILED: {resp.status_code}")
        return {}
    result = resp.json()
    if not result.get("success", True):
        print(f"  [{label}] API error: {result.get('msg')}")
        return {}
    return result.get("data", {})


def print_flat(data, prefix="", indent=2):
    if isinstance(data, dict):
        for k, v in sorted(data.items()):
            if isinstance(v, (dict, list)):
                print(f"{' '*indent}{prefix}{k}:")
                print_flat(v, prefix="  ", indent=indent+2)
            else:
                print(f"{' '*indent}{prefix}{k} = {v}")
    elif isinstance(data, list):
        for i, item in enumerate(data):
            if isinstance(item, dict):
                print(f"{' '*indent}{prefix}[{i}]:")
                print_flat(item, prefix="  ", indent=indent+2)
            else:
                print(f"{' '*indent}{prefix}[{i}] = {item}")


def main():
    creds = load_credentials()

    # Auth
    path = "/oauth/token"
    body = json.dumps({"username": creds["username"], "password": creds["password"], "grant_type": "password", "client_id": "openapi"}, separators=(",", ":"))
    nonce = str(uuid.uuid4())
    md5 = compute_md5(body)
    text = "\n".join(["POST", "application/json", md5, "application/json", "", f"x-ca-key:{creds['app_key']}", f"x-ca-nonce:{nonce}", path])
    sig = compute_hmac(text, creds["app_secret"])
    headers = {"Content-Type": "application/json", "Accept": "application/json", "Content-MD5": md5, "X-Ca-Key": creds["app_key"], "X-Ca-Nonce": nonce, "X-Ca-Signature": sig, "X-Ca-Signature-Headers": "x-ca-key,x-ca-nonce"}

    resp = requests.post(f"{OFFICIAL_API_BASE}{path}", headers=headers, data=body)
    if resp.status_code != 200:
        print(f"Auth FAILED: {resp.status_code} {resp.text[:200]}")
        return
    token = resp.json()["data"]["access_token"]
    bearer = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    print(f"Auth OK\n")

    # Get plant ID
    plants = get_data(f"{UNOFFICIAL_API_BASE}/api/v1/plants?page=1&limit=10&name=&status=", bearer, "plants")
    plant_id = plants.get("infos", [{}])[0].get("id")
    print(f"Plant ID: {plant_id}\n")

    sn = creds["inverter_sn"]

    sections = [
        ("1. PLANT FLOW", f"/api/v1/plant/energy/{plant_id}/flow"),
        ("2. BATTERY", f"/api/v1/inverter/battery/{sn}/realtime?sn={sn}&lan=en"),
        ("3. GRID", f"/api/v1/inverter/grid/{sn}/realtime?sn={sn}"),
        ("4. LOAD", f"/api/v1/inverter/load/{sn}/realtime?sn={sn}"),
        ("5. PV INPUT", f"/api/v1/inverter/{sn}/realtime/input"),
        ("6. INVERTER OUTPUT", f"/api/v1/inverter/{sn}/realtime/output"),
        ("7. SETTINGS", f"/api/v1/common/setting/{sn}/read"),
        ("8. PLANT DETAILS", f"/api/v1/plant/{plant_id}?lan=en"),
    ]

    for title, endpoint in sections:
        print("=" * 70)
        print(title)
        print("=" * 70)
        data = get_data(f"{UNOFFICIAL_API_BASE}{endpoint}", bearer, title)
        print_flat(data)
        print()

    print("DONE")


if __name__ == "__main__":
    main()
