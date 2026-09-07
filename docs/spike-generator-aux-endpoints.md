# Spike: Discover Generator/AUX Parameter API Endpoints

## What We Found (No Spike Needed!)

The `Solar-Sunsynk` ServiceGuide.md already documents the JSON field names for
generator/AUX parameters. The write endpoint is the same settings endpoint used
for all other writes.

### Generator/AUX JSON Keys

| Parameter | JSON Key | Range |
|-----------|----------|-------|
| SmartLoad mode | `loadMode` | 0=Gen Input, 1=Aux Load, 2=Micro Inverter |
| Gen peak-shaving | `genPeakShaving` | 0/1 |
| Gen peak-shaving power | `genPeakPower` | 500–30000 W |
| Generator OFF SOC | `genOffCap` | 0–100 % |
| Generator ON SOC | `genOnCap` | 0–100 % |
| Gen connect to grid | `genConnectGrid` | 0/1 |
| Generator min solar | `genMinSolar` | W |
| Generator OFF voltage | `genOffVolt` | V |
| Generator ON voltage | `genOnVolt` | V |
| AC couple upper freq | `acCoupleFreqUpper` | Hz |
| Grid peak-shaving | `gridPeakShaving` | 0/1 |
| Grid peak-shaving power | `gridPeakPower` | W |

Source: https://github.com/MorneSaunders360/Solar-Sunsynk/blob/main/ServiceGuide.md

---

## Original Spike Instructions (kept for reference)

Capture the API endpoint paths, request bodies, and response shapes for the
generator/AUX frequency and voltage limit settings in the Sunsynk Connect app.
These are needed to implement Epic 10 Story 10.2.

## What We Need to Find

For each of these settings, we need the **endpoint URL**, **HTTP method**,
**request body**, and **response shape**:

- Grid frequency high limit (Hz)
- Grid frequency low limit (Hz)
- AUX frequency high limit (Hz)
- AUX frequency low limit (Hz)
- Grid voltage high limit (V)
- Grid voltage low limit (V)
- AUX voltage high limit (V)
- AUX voltage low limit (V)

---

## Option 1: mitmproxy (macOS/Linux — Recommended)

### Step 1: Install mitmproxy

```bash
brew install mitmproxy   # macOS
# or
pip install mitmproxy    # any platform
```

### Step 2: Start the proxy

```bash
mitmweb --listen-port 8080
```

This opens a web UI at `http://localhost:8081` where you can see intercepted requests.

### Step 3: Configure your phone

1. On your phone, go to **WiFi Settings** → tap your network → **Configure Proxy**
2. Set **Manual** proxy:
   - Server: your Mac's local IP (find it with `ipconfig getifaddr en0`)
   - Port: `8080`

### Step 4: Install the mitmproxy CA certificate on your phone

1. On your phone's browser, go to `http://mitm.it`
2. Tap the certificate for your platform (iOS or Android) and install it
3. On iOS: go to **Settings → General → VPN & Device Management** → trust the certificate
4. On Android: go to **Settings → Security → Install from storage**

### Step 5: Capture the requests

1. Open the Sunsynk Connect app on your phone
2. Navigate to your inverter → **Settings** → look for **Grid** or **Protection** settings
3. Find the frequency/voltage limit fields
4. **Change a value** (e.g. change grid frequency high from 52Hz to 52.1Hz)
5. Tap **Save** or **Confirm**
6. In the mitmweb UI (`http://localhost:8081`), look for POST/PUT requests to `api.sunsynk.net`

### Step 6: Record what you find

For each request, note:
- **URL** (e.g. `https://api.sunsynk.net/api/v1/inverter/TEST123456/settings`)
- **Method** (GET/POST/PUT)
- **Request body** (the JSON payload)
- **Response body** (the JSON response)

---

## Option 2: Charles Proxy (GUI, easier for beginners)

1. Download [Charles Proxy](https://www.charlesproxy.com/) (free trial)
2. Install Charles SSL certificate on your phone (Help → SSL Proxying → Install Charles Root Certificate on a Mobile Device)
3. Enable SSL Proxying for `*.sunsynk.net` (Proxy → SSL Proxying Settings → Add `*.sunsynk.net`)
4. Set your phone's proxy to your Mac's IP:8888
5. Open Sunsynk app, change a generator/AUX setting, save
6. In Charles, find the request to `api.sunsynk.net` and copy the URL + body

---

## Option 3: Android with HTTP Toolkit (easiest, no certificate install needed on rooted devices)

1. Install [HTTP Toolkit](https://httptoolkit.com/) on your Mac
2. Connect your Android phone via USB
3. HTTP Toolkit intercepts traffic automatically
4. Open Sunsynk app, change a setting, capture the request

---

## What to Paste Back

Once you've captured the requests, paste the following into the chat:

```
Endpoint: POST https://api.sunsynk.net/api/v1/...
Headers: Authorization: Bearer ...
Request body:
{
  "...": "..."
}

Response:
{
  "code": 0,
  "data": {...},
  "success": true
}
```

I'll immediately implement `api/unofficial.py` write methods and the Epic 10 entities.

---

## Alternative: Check Existing Community Resources

Before running mitmproxy, check if someone has already documented these endpoints:

- [Solar-Sunsynk ServiceGuide.md](https://github.com/MorneSaunders360/Solar-Sunsynk/blob/main/ServiceGuide.md)
- [4x4community Demystifying the Sunsynk API thread](https://www.4x4community.co.za/forum/showthread.php/366452-Demystifying-the-Sunsynk-API)
- [kellerza/sunsynk sensor definitions](https://github.com/kellerza/sunsynk/tree/main/src/sunsynk/definitions)

The `kellerza/sunsynk` library already has Modbus register mappings for these
parameters — if the cloud API uses the same field names, we can infer the
endpoint structure from the existing write implementations in `Solar-Sunsynk`.
