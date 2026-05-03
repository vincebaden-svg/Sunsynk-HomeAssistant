# Setting Up Email Notifications

This guide walks you through setting up email notifications for the Sunsynk integration.

## Step 1: Configure SMTP in Home Assistant

Add this to your `configuration.yaml` (example using Gmail):

```yaml
notify:
  - name: email
    platform: smtp
    server: smtp.gmail.com
    port: 587
    starttls: true
    username: "your.email@gmail.com"
    password: "your_app_password"
    sender: "your.email@gmail.com"
    recipient:
      - "recipient@example.com"
```

> **Gmail users:** Use an [App Password](https://support.google.com/accounts/answer/185833), not your regular password. Enable 2FA first, then generate an App Password under Google Account → Security.

Restart Home Assistant after saving.

## Step 2: Test It

In HA Developer Tools → Services, call:
```yaml
service: notify.email
data:
  title: "Test from Sunsynk"
  message: "Email notifications are working!"
```

## Step 3: Install a Blueprint

Go to **Settings → Blueprints** and find the Sunsynk blueprints. Click **Grid Failure Load Management**, select `notify.email` as the notification service, and save.

## Example Automation YAML

```yaml
automation:
  - alias: "Sunsynk Daily Summary Email"
    trigger:
      - platform: event
        event_type: sunsynk_daily_summary
    action:
      - service: notify.email
        data:
          title: "Daily Solar Summary - {{ trigger.event.data.date }}"
          message: >
            Solar generated: {{ trigger.event.data.pv_energy_today }} kWh
            Grid import: {{ trigger.event.data.grid_import_today }} kWh
            Load: {{ trigger.event.data.load_energy_today }} kWh
```
