#!/usr/bin/env python3
from __future__ import annotations

import os

from google_auth_oauthlib.flow import InstalledAppFlow


SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/gmail.labels",
    "https://www.googleapis.com/auth/calendar",
]


def main() -> None:
    client_path = os.getenv("GOOGLE_OAUTH_CLIENT_JSON_PATH", "credentials.json")
    token_path = os.getenv("GOOGLE_OAUTH_TOKEN_JSON_PATH", "token.json")

    flow = InstalledAppFlow.from_client_secrets_file(client_path, SCOPES)
    creds = flow.run_local_server(port=0)
    with open(token_path, "w", encoding="utf-8") as f:
        f.write(creds.to_json())

    print(f"Saved OAuth token to {token_path}")


if __name__ == "__main__":
    main()
