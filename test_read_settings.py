#!/usr/bin/env python3
"""Quick script to read current inverter settings and show key values."""
import base64, hashlib, hmac, json, os, uuid, requests

OFFICIAL_API_BASE = "https://openapi.sunsynk.net"
UNOFFICIAL_API_BASE = "https://api.sunsynk.net"

# Credentials (set env vars)
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
token = resp.json()["data"]["access_token"]
print(f"Auth OK (token: {token[:15]}...)\n")

# Read settings
bearer = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
url = f"{UNOFFICIAL_API_BASE}/api/v1/common/setting/{INVERTER_SN}/read"
resp = requests.get(url, headers=bearer)
data = resp.json().get("data", {})

# Print key settings
print("=== Current Inverter Settings ===\n")
keys_of_interest = [
    "battMode", "sysWorkMode", "solarSell", "energyMode", "peakAndVallery",
    "pvMaxLimit", "zeroExportPower", "solarMaxSellPower",
    "sellTime1", "sellTime2", "sellTime3", "sellTime4", "sellTime5", "sellTime6",
    "cap1", "cap2", "cap3", "cap4", "cap5", "cap6",
    "time1on", "time2on", "time3on", "time4on", "time5on", "time6on",
    "genTime1on", "genTime2on", "genTime3on", "genTime4on", "genTime5on", "genTime6on",
    "sellTime1Pac", "sellTime2Pac", "sellTime3Pac", "sellTime4Pac", "sellTime5Pac", "sellTime6Pac",
    "batteryShutdownCap", "batteryRestartCap", "batteryMaxCurrentCharge",
    "loadMode", "genPeakShaving", "gridPeakShaving",
]

for key in keys_of_interest:
    val = data.get(key, "NOT PRESENT")
    print(f"  {key:30s} = {val}")

print(f"\n=== Full response ({len(data)} keys) ===\n")
for k, v in sorted(data.items()):
    print(f"  {k:30s} = {v}")
