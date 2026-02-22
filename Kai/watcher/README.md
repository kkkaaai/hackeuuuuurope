# Watcher

Background polling tasks for linked accounts. Each task polls an integration, compares current vs previous state, asks the LLM for meaningful changes, proposes proactive actions, and asks the user for approval via WhatsApp.

## Quick start

1) Edit `watcher/tasks.py` and set:
   - `enabled: True`
   - `wa_id` for the recipient
   - `credentials` for the integration
2) Install a cron entry using `watcher/cron.sample`.
3) Run once locally to validate:
   ```bash
   python -m watcher.runner
   ```

## Task format

Each task includes:
- `id`: unique identifier
- `script`: script path to run
- `enabled`: toggle
- `interval_seconds`: frequency (default 3600)
- `config`: integration-specific configuration

## Integrations

Google integrations are stubbed and off by default:
- Google Calendar (`watcher/integrations/google_calendar.py`)
- Gmail (`watcher/integrations/google_gmail.py`)
- Google Drive (`watcher/integrations/google_drive.py`)
- Google Contacts (`watcher/integrations/google_contacts.py`)
- Google Tasks (`watcher/integrations/google_tasks.py`)

Wire up OAuth/API access inside each integration module's `fetch_state` function.

## Approval flow

When actions are proposed, the watcher sends a WhatsApp prompt:
`approve <action_id>` or `decline <action_id>`

Approvals are executed via the LLM (drafts, research summaries, etc.) and logged as notifications.
