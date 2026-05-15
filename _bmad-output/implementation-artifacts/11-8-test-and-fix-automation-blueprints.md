# Story 11.8: Test and Fix Automation Blueprints

**Status:** in-progress
**Epic:** 11 — Post-Deployment Hardening
**Created:** 2026-05-15

## Issues Found

1. **notify_target uses text selector** — should use `action` selector for HA 2024+ notify services
2. **Message templates don't use trigger data** — `{soc}` placeholders won't render; need Jinja2 `{{ trigger.event.data.soc }}`
3. **summer_load_priority triggers on wrong event** — uses `sunsynk_daily_summary` (fires once/day) instead of a state-based trigger
4. **pool_motor has no "turn back on" logic** — only turns off, never restores
5. **source_url is wrong** — points to `vinbaden/ha-sunsynk` not `vincebaden-svg/Sunsynk-HomeAssistant`
6. **control_switch optional handling** — template check `{{ control_switch != {} }}` won't work in blueprint context

## Fixes Applied

All 5 blueprints rewritten with correct HA 2024+ patterns.
