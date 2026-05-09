#!/usr/bin/env python3
"""Google Workspace OAuth setup. Run once to generate token.json."""
import os
from pathlib import Path
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

SCOPES = [
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/spreadsheets',
]

GWS_DIR   = Path(__file__).parent
CREDS_FILE = GWS_DIR / "credentials.json"
TOKEN_FILE = GWS_DIR / "token.json"

def get_credentials():
    creds = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CREDS_FILE.exists():
                print(f"ERROR: Put your OAuth credentials at {CREDS_FILE}")
                print("Get them from: console.cloud.google.com > APIs > Credentials > OAuth 2.0")
                exit(1)
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDS_FILE), SCOPES)
            creds = flow.run_local_server(port=0)
        TOKEN_FILE.write_text(creds.to_json())
    return creds

if __name__ == "__main__":
    creds = get_credentials()
    print(f"✅ Authenticated. Token saved to {TOKEN_FILE}")
