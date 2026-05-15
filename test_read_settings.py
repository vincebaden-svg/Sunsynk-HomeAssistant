#!/usr/bin/env python3
"""Read current inverter settings and display key values.

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

    # Read settings
    sn = creds["inverter_sn"]
    url = f"{UNOFFICIAL_API_BASE}/api/v1/common/setting/{sn}/read"
    resp = requests.get(url, headers=bearer)
    data = resp.json().get("data", {})

    print("=== Current Inverter Settings ===\n")
    for k, v in sorted(data.items()):
        print(f"  {k:30s} = {v}")


if __name__ == "__main__":
    main()
