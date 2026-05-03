# Setting Up Telegram Notifications

This guide walks you through setting up Telegram notifications for the Sunsynk integration.

## Step 1: Create a Telegram Bot

1. Open Telegram and search for **@BotFather**
2. Send `/newbot` and follow the prompts
3. Choose a name (e.g. "My Sunsynk Bot") and a username (must end in `bot`, e.g. `my_sunsynk_bot`)
4. BotFather will give you a **bot token** — save it (looks like `123456789:ABCdef...`)

## Step 2: Get Your Chat ID

1. Start a conversation with your new bot (search for it and send `/start`)
2. Visit this URL in your browser (replace `YOUR_TOKEN`):
   ```
   https://api.telegram.org/botYOUR_TOKEN/getUpdates
   ```
3. Look for `"chat":{"id":` in the response — that number is your **chat ID**

## Step 3: Configure Home Assistant

Add this to your `configuration.yaml`:

```yaml
telegram_bot:
  - platform: polling
    api_key: "YOUR_BOT_TOKEN"
    allowed_chat_ids:
      - YOUR_CHAT_ID

notify:
  - name: telegram
    platform: telegram
    chat_id: YOUR_CHAT_ID
```

Restart Home Assistant after saving.

## Step 4: Test It

In HA Developer Tools → Services, call:
```yaml
service: notify.telegram
data:
  message: "Test from Sunsynk!"
```

## Step 5: Install a Blueprint

Go to **Settings → Blueprints** and find the Sunsynk blueprints. Click **Grid Failure Load Management**, select `notify.telegram` as the notification service, and save.

## Example Automation YAML

```yaml
automation:
  - alias: "Sunsynk Grid Failure Alert"
    trigger:
      - platform: event
        event_type: sunsynk_grid_failure
    action:
      - service: notify.telegram
        data:
          message: >
            ⚡ Grid failure! Battery at {{ trigger.event.data.battery_soc }}%.
            Please avoid heavy loads.
```
