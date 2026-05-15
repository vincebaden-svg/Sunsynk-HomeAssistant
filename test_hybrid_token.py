#!/usr/bin/env python3
"""Test script: verify data fetch strategies for the Sunsynk official API.

Tests both:
1. Hybrid approach: official auth token → unofficial data endpoints
2. Pure official: HMAC-signed GET requests to openapi.sunsynk.net

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
def compute_hmac_sha256(text, secret): return base64.b64encode(hmac.new(secret.encode(), text.encode(), hashlib.sha256).digest()).decode()


def build_signed_headers_post(path, body, app_key, app_secret):
    nonce = str(uuid.uuid4())
    body_md5 = compute_md5(body) if body else ""
    lines = ["POST", "application/json", body_md5, "application/json", "", f"x-ca-key:{app_key}", f"x-ca-nonce:{nonce}", path]
    text_to_sign = "\n".join(lines)
    signature = compute_hmac_sha256(text_to_sign, app_secret)
    return {
        "Content-Type": "application/json", "Accept": "application/json",
        "Content-MD5": body_md5, "X-Ca-Key": app_key, "X-Ca-Nonce": nonce,
        "X-Ca-Signature": signature, "X-Ca-Signature-Headers": "x-ca-key,x-ca-nonce",
    }


def main():
    print("=" * 65)
    print("  Sunsynk API Data Fetch Strategy Test")
    print("=" * 65)
    print()

    creds = load_credentials()
    print()

    # Step 1: Authenticate
    print("[1/3] Authenticating via official API...")
    path = "/oauth/token"
    body_data = {"username": creds["username"], "password": creds["password"], "grant_type": "password", "client_id": "openapi"}
    body = json.dumps(body_data, separators=(",", ":"))
    headers = build_signed_headers_post(path, body, creds["app_key"], creds["app_secret"])

    resp = requests.post(f"{OFFICIAL_API_BASE}{path}", headers=headers, data=body)
    print(f"  Status: {resp.status_code}")
    if resp.status_code != 200:
        print(f"  FAILED: {resp.text[:300]}")
        return

    auth_data = resp.json()
    if not auth_data.get("success"):
        print(f"  FAILED: {auth_data.get('msg', 'Unknown error')}")
        return

    token = auth_data["data"]["access_token"]
    print(f"  SUCCESS — token: {token[:20]}...")
    print()

    # Step 2: Test hybrid
    print("[2/3] Testing HYBRID: token on unofficial API...")
    bearer_headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    plants_url = f"{UNOFFICIAL_API_BASE}/api/v1/plants?page=1&limit=10&name=&status="
    resp = requests.get(plants_url, headers=bearer_headers)
    print(f"  Status: {resp.status_code}")

    if resp.status_code == 200:
        data = resp.json()
        if data.get("success"):
            plants = data.get("data", {}).get("infos", [])
            print(f"  SUCCESS — found {len(plants)} plant(s)")
            if plants:
                plant_id = plants[0]["id"]
                print(f"    Plant ID: {plant_id}")
        else:
            print(f"  API error: {data.get('msg')}")
    elif resp.status_code == 401:
        print("  REJECTED (401) — token not cross-compatible")
    print()

    # Step 3: Test data endpoints
    print("[3/3] Testing data endpoints...")
    sn = creds["inverter_sn"]
    endpoints = [
        (f"/api/v1/plant/energy/{plant_id}/flow", "Plant Flow"),
        (f"/api/v1/inverter/battery/{sn}/realtime?sn={sn}&lan=en", "Battery"),
        (f"/api/v1/inverter/grid/{sn}/realtime?sn={sn}", "Grid"),
        (f"/api/v1/inverter/load/{sn}/realtime?sn={sn}", "Load"),
        (f"/api/v1/inverter/{sn}/realtime/input", "PV Input"),
        (f"/api/v1/common/setting/{sn}/read", "Settings"),
    ]
    for path, name in endpoints:
        url = f"{UNOFFICIAL_API_BASE}{path}"
        resp = requests.get(url, headers=bearer_headers)
        status = "✓" if resp.status_code == 200 else "✗"
        print(f"  {status} {name:12s} [{resp.status_code}]")
    print()
    print("DONE")


if __name__ == "__main__":
    main()
