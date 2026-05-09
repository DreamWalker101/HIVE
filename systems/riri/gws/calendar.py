#!/usr/bin/env python3
"""Google Calendar CLI for RiRi."""
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from auth import get_credentials
from googleapiclient.discovery import build

def main():
    creds   = get_credentials()
    service = build('calendar', 'v3', credentials=creds)

    cmd = sys.argv[1] if len(sys.argv) > 1 else "list"

    if cmd == "list":
        days  = int(sys.argv[2]) if len(sys.argv) > 2 else 7
        now   = datetime.now(timezone.utc)
        end   = now + timedelta(days=days)
        events = service.events().list(
            calendarId='primary', timeMin=now.isoformat(), timeMax=end.isoformat(),
            singleEvents=True, orderBy='startTime', maxResults=20
        ).execute().get('items', [])
        for e in events:
            start = e['start'].get('dateTime', e['start'].get('date', '?'))[:16]
            print(f"[{start}] {e.get('summary', 'Untitled')}")
        if not events:
            print(f"No events in the next {days} days.")

    elif cmd == "create":
        title, start_str, end_str = sys.argv[2], sys.argv[3], sys.argv[4]
        fmt = "%Y-%m-%d %H:%M"
        tz  = "Asia/Karachi"
        event = {
            'summary': title,
            'start':   {'dateTime': datetime.strptime(start_str, fmt).isoformat(), 'timeZone': tz},
            'end':     {'dateTime': datetime.strptime(end_str,   fmt).isoformat(), 'timeZone': tz},
        }
        e = service.events().insert(calendarId='primary', body=event).execute()
        print(f"✅ Created: {e.get('htmlLink')}")

if __name__ == "__main__":
    main()
