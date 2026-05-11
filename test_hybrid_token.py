#!/usr/bin/env python3
"""Test script: verify data fetch strategies for the Sunsynk official API.

Tests both:
1. Hybrid approach: official auth token → unofficial data endpoints
2. Pure official: HMAC-signed GET requests to openapi.sunsynk.net

Usage:
    python3 test_hybrid_token.py

Set environment variables to skip prompts:
    SUNSYNK_APP_KEY, SUNSYNK_APP_SECRET, SUNSYNK_USERNAME, SUNSYNK_PASSWORD
"""
import base64
import hashlib
import hmac
import json
import os
import uuid

import requests

# --- Configuration ---
OFFICIAL_API_BASE = "https://openapi.sunsynk.net"
UNOFFICIAL_API_BASE = "https://api.sunsynk.net"


def get_input(prompt: str, env_var: str, secret: bool = False) -> str:
    """Get value from env or prompt."""
    value = os.environ.get(env_var, "")
    if value:
        display = "***" if secret else value
        print(f"  {prompt}: {display} (from ${env_var})")
        return value
    if secret:
        import getpass
        return getpass.getpass(f"  {prompt}: ")
    return input(f"  {prompt}: ")


def compute_md5(data: str) -> str:
    """Base64-encoded MD5."""
    return base64.b64encode(hashlib.md5(data.encode()).digest()).decode()


def compute_hmac_sha256(text: str, secret: str) -> str:
    """Base64-encoded HMAC-SHA256."""
    sig = hmac.new(secret.encode(), text.encode(), hashlib.sha256).digest()
    return base64.b64encode(sig).decode()


def build_url_to_sign(path: str, query_params: dict | None = None) -> str:
    """Build URL portion of textToSign with sorted query params."""
    if not query_params:
        return path
    sorted_params = sorted(query_params.items())
    qs = "&".join(f"{k}={v}" for k, v in sorted_params)
    return f"{path}?{qs}"


def build_signed_headers_post(path: str, body: str, app_key: str, app_secret: str) -> dict:
    """Build HMAC-signed headers for POST (auth)."""
    nonce = str(uuid.uuid4())
    body_md5 = compute_md5(body) if body else ""

    lines = [
        "POST",
        "application/json",
        body_md5,
        "application/json",
        "",
        f"x-ca-key:{app_key}",
        f"x-ca-nonce:{nonce}",
        path,
    ]
    text_to_sign = "\n".join(lines)
    signature = compute_hmac_sha256(text_to_sign, app_secret)

    return {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Content-MD5": body_md5,
        "X-Ca-Key": app_key,
        "X-Ca-Nonce": nonce,
        "X-Ca-Signature": signature,
        "X-Ca-Signature-Headers": "x-ca-key,x-ca-nonce",
    }


def build_signed_headers_get(
    path: str, app_key: str, app_secret: str,
    query_params: dict | None = None,
    content_type: str = "",
    token: str | None = None,
) -> dict:
    """Build HMAC-signed headers for GET (data).

    content_type: "" for no body (standard GET), or "application/json" (variant)
    """
    nonce = str(uuid.uuid4())
    url_to_sign = build_url_to_sign(path, query_params)

    lines = [
        "GET",
        "application/json",   # accept
        "",                   # Content-MD5 (empty for GET)
        content_type,         # content-type (empty or application/json)
        "",                   # Date placeholder
        f"x-ca-key:{app_key}",
        f"x-ca-nonce:{nonce}",
        url_to_sign,
    ]
    text_to_sign = "\n".join(lines)
    signature = compute_hmac_sha256(text_to_sign, app_secret)

    headers = {
        "Accept": "application/json",
        "X-Ca-Key": app_key,
        "X-Ca-Nonce": nonce,
        "X-Ca-Signature": signature,
        "X-Ca-Signature-Headers": "x-ca-key,x-ca-nonce",
    }
    if content_type:
        headers["Content-Type"] = content_type
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def main():
    print("=" * 65)
    print("  Sunsynk API Data Fetch Strategy Test")
    print("=" * 65)
    print()

    # Gather credentials
    print("[1/5] Credentials")
    app_key = get_input("App Key", "SUNSYNK_APP_KEY")
    app_secret = get_input("App Secret", "SUNSYNK_APP_SECRET", secret=True)
    username = get_input("Username", "SUNSYNK_USERNAME")
    password = get_input("Password", "SUNSYNK_PASSWORD", secret=True)
    print()

    # ─── Step 1: Authenticate via official API ───
    print("[2/5] Authenticating via official API (openapi.sunsynk.net)...")
    path = "/oauth/token"
    body_data = {
        "username": username,
        "password": password,
        "grant_type": "password",
        "client_id": "openapi",
    }
    body = json.dumps(body_data, separators=(",", ":"))
    headers = build_signed_headers_post(path, body, app_key, app_secret)

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

    # ─── Step 2: Test hybrid approach ───
    print("[3/5] Testing HYBRID: token on unofficial API (api.sunsynk.net)...")
    plants_url = f"{UNOFFICIAL_API_BASE}/api/v1/plants?page=1&limit=10&name=&status="
    bearer_headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}

    resp = requests.get(plants_url, headers=bearer_headers)
    print(f"  Status: {resp.status_code}")

    hybrid_works = False
    plant_id = None
    inverter_sn = None
    if resp.status_code == 200:
        data = resp.json()
        if data.get("success"):
            plants = data.get("data", {}).get("infos", [])
            print(f"  SUCCESS — found {len(plants)} plant(s)")
            for p in plants:
                print(f"    • Plant ID: {p.get('id')}, Name: {p.get('name', 'N/A')}")
            if plants:
                plant_id = plants[0]["id"]
            hybrid_works = True
        else:
            print(f"  API returned success=false: {data.get('msg', 'Unknown')}")
    elif resp.status_code == 401:
        print(f"  REJECTED (401) — token not cross-compatible")
    else:
        print(f"  Unexpected: {resp.status_code} — {resp.text[:200]}")
    print()

    # ─── Step 2b: Test expanded data endpoints ───
    if hybrid_works and plant_id:
        print("[3b/5] Testing expanded data endpoints...")
        print()

        # Get inverter serial from plant inverters list
        inv_url = f"{UNOFFICIAL_API_BASE}/api/v1/plant/{plant_id}/inverters?page=1&limit=10&status=-1&type=-2"
        resp = requests.get(inv_url, headers=bearer_headers)
        if resp.status_code == 200:
            inv_data = resp.json()
            inverters = inv_data.get("data", {}).get("infos", [])
            if inverters:
                inverter_sn = inverters[0].get("sn")
                print(f"  Inverter SN: {inverter_sn}")
            else:
                print("  No inverters found in plant")
        else:
            print(f"  /inverters: {resp.status_code}")

        if inverter_sn:
            endpoints = [
                (f"/api/v1/plant/energy/{plant_id}/flow", "Plant Flow"),
                (f"/api/v1/inverter/battery/{inverter_sn}/realtime?sn={inverter_sn}&lan=en", "Battery"),
                (f"/api/v1/inverter/grid/{inverter_sn}/realtime?sn={inverter_sn}", "Grid"),
                (f"/api/v1/inverter/load/{inverter_sn}/realtime?sn={inverter_sn}", "Load"),
                (f"/api/v1/inverter/{inverter_sn}/realtime/input", "PV Input"),
                (f"/api/v1/common/setting/{inverter_sn}/read", "Settings"),
            ]
            for path, name in endpoints:
                url = f"{UNOFFICIAL_API_BASE}{path}"
                resp = requests.get(url, headers=bearer_headers)
                status = "✓" if resp.status_code == 200 else "✗"
                detail = ""
                if resp.status_code == 200:
                    rdata = resp.json().get("data", {})
                    # Show a few key fields
                    if name == "Battery":
                        detail = f"soc={rdata.get('soc')} power={rdata.get('power')}W"
                    elif name == "Grid":
                        detail = f"pac={rdata.get('pac')}W fac={rdata.get('fac')}Hz"
                    elif name == "Load":
                        detail = f"totalPower={rdata.get('totalPower')}W"
                    elif name == "PV Input":
                        detail = f"pac={rdata.get('pac')}W etoday={rdata.get('etoday')}kWh"
                    elif name == "Plant Flow":
                        detail = f"pv={rdata.get('pvPower')}W batt={rdata.get('battPower')}W"
                    elif name == "Settings":
                        detail = f"sysWorkMode={rdata.get('sysWorkMode')}"
                print(f"  {status} {name:12s} [{resp.status_code}] {detail}")
        print()

    # ─── Step 3: Test pure official GET (variant 1: empty content-type) ───
    print("[4/5] Testing PURE OFFICIAL: HMAC-signed GET /plants...")
    print()

    query_params = {"limit": "10", "page": "1"}
    sorted_params = sorted(query_params.items())
    qs = "&".join(f"{k}={v}" for k, v in sorted_params)

    # Variant A: empty content-type, no Bearer token
    print("  Variant A: empty content-type, no Bearer token")
    headers_a = build_signed_headers_get(
        "/plants", app_key, app_secret,
        query_params=query_params, content_type="", token=None
    )
    url = f"{OFFICIAL_API_BASE}/plants?{qs}"
    resp = requests.get(url, headers=headers_a)
    print(f"    Status: {resp.status_code}")
    if resp.status_code == 200:
        print(f"    BODY: {resp.text[:200]}")
    else:
        print(f"    Body: {resp.text[:150]}")
    print()

    # Variant B: empty content-type, WITH Bearer token
    print("  Variant B: empty content-type, WITH Bearer token")
    headers_b = build_signed_headers_get(
        "/plants", app_key, app_secret,
        query_params=query_params, content_type="", token=token
    )
    resp = requests.get(url, headers=headers_b)
    print(f"    Status: {resp.status_code}")
    if resp.status_code == 200:
        print(f"    BODY: {resp.text[:200]}")
    else:
        print(f"    Body: {resp.text[:150]}")
    print()

    # Variant C: application/json content-type, WITH Bearer token
    print("  Variant C: application/json content-type, WITH Bearer token")
    headers_c = build_signed_headers_get(
        "/plants", app_key, app_secret,
        query_params=query_params, content_type="application/json", token=token
    )
    resp = requests.get(url, headers=headers_c)
    print(f"    Status: {resp.status_code}")
    if resp.status_code == 200:
        print(f"    BODY: {resp.text[:200]}")
    else:
        print(f"    Body: {resp.text[:150]}")
    print()

    # Variant D: application/json content-type, no Bearer token
    print("  Variant D: application/json content-type, no Bearer token")
    headers_d = build_signed_headers_get(
        "/plants", app_key, app_secret,
        query_params=query_params, content_type="application/json", token=None
    )
    resp = requests.get(url, headers=headers_d)
    print(f"    Status: {resp.status_code}")
    if resp.status_code == 200:
        print(f"    BODY: {resp.text[:200]}")
    else:
        print(f"    Body: {resp.text[:150]}")
    print()

    # Variant E: no query params in signature (just path)
    print("  Variant E: empty content-type, Bearer, NO query params in signature")
    headers_e = build_signed_headers_get(
        "/plants", app_key, app_secret,
        query_params=None, content_type="", token=token
    )
    resp = requests.get(url, headers=headers_e)
    print(f"    Status: {resp.status_code}")
    if resp.status_code == 200:
        print(f"    BODY: {resp.text[:200]}")
    else:
        print(f"    Body: {resp.text[:150]}")
    print()

    # ─── Summary ───
    print("[5/5] RESULTS SUMMARY")
    print("─" * 65)
    if hybrid_works:
        print("  ✓ HYBRID WORKS — official auth token accepted by unofficial API")
        print("    → Use official.py as-is (hybrid strategy)")
    else:
        print("  ✗ HYBRID FAILED — token not cross-compatible")
    print()
    print("  Review the GET signing results above to determine which variant")
    print("  (if any) returns 200. That tells us the correct signing format.")
    print()
    print("  Status code meanings:")
    print("    200 = Success (correct signing)")
    print("    400 = Bad Request (signing format wrong)")
    print("    401 = Unauthorized (no/invalid auth)")
    print("    404 = Endpoint doesn't exist at this path")
    print("    403 = Forbidden (account/permission issue)")


if __name__ == "__main__":
    main()
