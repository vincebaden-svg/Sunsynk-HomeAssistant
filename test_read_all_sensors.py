#!/usr/bin/env python3
"""Read all sensor data from every Sunsynk API endpoint and display values.

Usage:
    SUNSYNK_APP_SECRET="xxx" SUNSYNK_PASSWORD="xxx" python3 test_read_all_sensors.py
"""
import base64, hashlib, hmac, json, os, uuid, requests

OFFICIAL_API_BASE = "https://openapi.sunsynk.net"
UNOFFICIAL_API_BASE = "https://api.sunsynk.net"

APP_KEY = os.environ.get("SUNSYNK_APP_KEY", "")
APP_SECRET = os.environ.get("SUNSYNK_APP_SECRET", "")
USERNAME = os.environ.get("SUNSYNK_USERNAME", "")
PASSWORD = os.environ.get("SUNSYNK_PASSWORD", "")
INVERTER_SN = os.environ.get("SUNSYNK_INVERTER_SN", "")

def compute_md5(data): return base64.b64encode(hashlib.md5(data.encode()).digest()).decode()
def compute_hmac(text, secret): return base64.b64encode(hmac.new(secret.encode(), text.encode(), hashlib.sha256).digest()).decode()

# Auth
if not APP_SECRET:
    import getpass
    APP_SECRET = getpass.getpass("App Secret: ")
if not PASSWORD:
    import getpass
    PASSWORD = getpass.getpass("Password: ")

path = "/oauth/token"
body = json.dumps({"username":USERNAME,"password":PASSWORD,"grant_type":"password","client_id":"openapi"}, separators=(",",":"))
nonce = str(uuid.uuid4())
md5 = compute_md5(body)
text = "\n".join(["POST","application/json",md5,"application/json","",f"x-ca-key:{APP_KEY}",f"x-ca-nonce:{nonce}",path])
sig = compute_hmac(text, APP_SECRET)
headers = {"Content-Type":"application/json","Accept":"application/json","Content-MD5":md5,"X-Ca-Key":APP_KEY,"X-Ca-Nonce":nonce,"X-Ca-Signature":sig,"X-Ca-Signature-Headers":"x-ca-key,x-ca-nonce"}

resp = requests.post(f"{OFFICIAL_API_BASE}{path}", headers=headers, data=body)
if resp.status_code != 200:
    print(f"Auth FAILED: {resp.status_code} {resp.text[:200]}")
    exit(1)
token = resp.json()["data"]["access_token"]
bearer = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
print(f"Auth OK\n")


def get_data(url, label):
    """Fetch and return data dict from an endpoint."""
    resp = requests.get(url, headers=bearer)
    if resp.status_code != 200:
        print(f"  [{label}] FAILED: {resp.status_code}")
        return {}
    result = resp.json()
    if not result.get("success", True):
        print(f"  [{label}] API error: {result.get('msg')}")
        return {}
    return result.get("data", {})


def print_flat(data, prefix="", indent=2):
    """Recursively print dict/list values in flat format."""
    if isinstance(data, dict):
        for k, v in sorted(data.items()):
            if isinstance(v, (dict, list)):
                print(f"{' '*indent}{prefix}{k}:")
                print_flat(v, prefix=f"  ", indent=indent+2)
            else:
                print(f"{' '*indent}{prefix}{k} = {v}")
    elif isinstance(data, list):
        for i, item in enumerate(data):
            if isinstance(item, dict):
                print(f"{' '*indent}{prefix}[{i}]:")
                print_flat(item, prefix=f"  ", indent=indent+2)
            else:
                print(f"{' '*indent}{prefix}[{i}] = {item}")
    else:
        print(f"{' '*indent}{prefix}{data}")


# Get plant ID
plants = get_data(f"{UNOFFICIAL_API_BASE}/api/v1/plants?page=1&limit=10&name=&status=", "plants")
plant_id = plants.get("infos", [{}])[0].get("id")
print(f"Plant ID: {plant_id}")
print()

sn = INVERTER_SN

print("=" * 70)
print("1. PLANT FLOW — /api/v1/plant/energy/{plant_id}/flow")
print("=" * 70)
data = get_data(f"{UNOFFICIAL_API_BASE}/api/v1/plant/energy/{plant_id}/flow", "flow")
print_flat(data)
print()

print("=" * 70)
print("2. BATTERY — /api/v1/inverter/battery/{sn}/realtime")
print("=" * 70)
data = get_data(f"{UNOFFICIAL_API_BASE}/api/v1/inverter/battery/{sn}/realtime?sn={sn}&lan=en", "battery")
print_flat(data)
print()

print("=" * 70)
print("3. GRID — /api/v1/inverter/grid/{sn}/realtime")
print("=" * 70)
data = get_data(f"{UNOFFICIAL_API_BASE}/api/v1/inverter/grid/{sn}/realtime?sn={sn}", "grid")
print_flat(data)
print()

print("=" * 70)
print("4. LOAD — /api/v1/inverter/load/{sn}/realtime")
print("=" * 70)
data = get_data(f"{UNOFFICIAL_API_BASE}/api/v1/inverter/load/{sn}/realtime?sn={sn}", "load")
print_flat(data)
print()

print("=" * 70)
print("5. PV INPUT — /api/v1/inverter/{sn}/realtime/input")
print("=" * 70)
data = get_data(f"{UNOFFICIAL_API_BASE}/api/v1/inverter/{sn}/realtime/input", "input")
print_flat(data)
print()

print("=" * 70)
print("6. INVERTER OUTPUT — /api/v1/inverter/{sn}/realtime/output")
print("=" * 70)
data = get_data(f"{UNOFFICIAL_API_BASE}/api/v1/inverter/{sn}/realtime/output", "output")
print_flat(data)
print()

print("=" * 70)
print("7. SETTINGS — /api/v1/common/setting/{sn}/read")
print("=" * 70)
data = get_data(f"{UNOFFICIAL_API_BASE}/api/v1/common/setting/{sn}/read", "settings")
print_flat(data)
print()

print("=" * 70)
print("8. PLANT DETAILS — /api/v1/plant/{plant_id}")
print("=" * 70)
data = get_data(f"{UNOFFICIAL_API_BASE}/api/v1/plant/{plant_id}?lan=en", "plant_details")
print_flat(data)
print()

print("=" * 70)
print("9. INVERTER LIST — /api/v1/plant/{plant_id}/inverters")
print("=" * 70)
data = get_data(f"{UNOFFICIAL_API_BASE}/api/v1/plant/{plant_id}/inverters?page=1&limit=10&status=-1&type=-2", "inverters")
print_flat(data)
print()

print("=" * 70)
print("DONE")
print("=" * 70)
