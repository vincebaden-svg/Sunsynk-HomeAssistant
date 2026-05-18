# Telegram Notification Setup (HA 2025.11+)

Since Home Assistant 2025.11, Telegram uses entity-based notifications. Each chat ID gets its own `notify` entity that you select in blueprints.

## Step 1: Create a Telegram Bot

1. Open Telegram, search for **@BotFather**
2. Send `/newbot`
3. Choose a name (e.g. "Home Assistant")
4. Choose a username (e.g. `my_ha_bot`)
5. Copy the **API token** (looks like `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

## Step 2: Get Your Chat ID

1. Search for your new bot in Telegram and send it any message (e.g. "hello")
2. Open this URL in a browser (replace YOUR_TOKEN):
   ```
   https://api.telegram.org/botYOUR_TOKEN/getUpdates
   ```
3. Find `"chat":{"id":123456789}` — that number is your **chat ID**

## Step 3: Add Telegram Integration in HA

1. Go to **Settings → Devices & Services → Add Integration**
2. Search for **Telegram Bot**
3. Choose **Polling** (works without exposing HA to the internet)
4. Enter:
   - API Key: your bot token from Step 1
   - Allowed Chat IDs: your chat ID from Step 2
5. Click Submit

## Step 4: Find Your Notify Entity

After adding the integration:

1. Go to **Settings → Devices & Services → Telegram Bot**
2. Click on the device
3. You'll see a `notify` entity like `notify.telegram_bot_123456789`
4. This is what you select in the Sunsynk blueprints

## Step 5: Use in Sunsynk Blueprints

1. Go to **Settings → Automations & Scenes → Blueprints**
2. Find any Sunsynk blueprint (e.g. "Grid Failure Notification")
3. Click **Create Automation**
4. In the **Notification Entity** dropdown, select your Telegram notify entity
5. Save

That's it — you'll receive Telegram messages when events fire.

## Troubleshooting

- **No notify entity appears:** Make sure you sent a message to the bot first, then re-add the integration
- **Messages not arriving:** Check the chat ID is correct and the bot token is valid
- **Multiple chats:** Add multiple chat IDs in Step 3 — each gets its own notify entity
