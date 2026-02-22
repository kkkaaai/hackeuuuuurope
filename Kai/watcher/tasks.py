"""Background task definitions.

Edit this file to enable tasks and set credentials.
"""

TASKS = [
    {
        "id": "google_calendar_watch",
        "script": "watcher/scripts/google_calendar_watch.py",
        "enabled": False,
        "interval_seconds": 3600,
        "config": {
            "account_type": "google_calendar",
            "user_id": "primary",
            "wa_id": "",
            "credentials": {},
        },
    },
    {
        "id": "google_gmail_watch",
        "script": "watcher/scripts/google_gmail_watch.py",
        "enabled": False,
        "interval_seconds": 3600,
        "config": {
            "account_type": "google_gmail",
            "user_id": "primary",
            "wa_id": "",
            "credentials": {},
        },
    },
    {
        "id": "google_drive_watch",
        "script": "watcher/scripts/google_drive_watch.py",
        "enabled": False,
        "interval_seconds": 3600,
        "config": {
            "account_type": "google_drive",
            "user_id": "primary",
            "wa_id": "",
            "credentials": {},
        },
    },
    {
        "id": "google_contacts_watch",
        "script": "watcher/scripts/google_contacts_watch.py",
        "enabled": False,
        "interval_seconds": 3600,
        "config": {
            "account_type": "google_contacts",
            "user_id": "primary",
            "wa_id": "",
            "credentials": {},
        },
    },
    {
        "id": "google_tasks_watch",
        "script": "watcher/scripts/google_tasks_watch.py",
        "enabled": False,
        "interval_seconds": 3600,
        "config": {
            "account_type": "google_tasks",
            "user_id": "primary",
            "wa_id": "",
            "credentials": {},
        },
    },
]
