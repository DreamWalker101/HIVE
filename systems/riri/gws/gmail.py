#!/usr/bin/env python3
"""Gmail CLI for RiRi."""
import sys, json, base64
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from auth import get_credentials
from googleapiclient.discovery import build

def main():
    creds   = get_credentials()
    service = build('gmail', 'v1', credentials=creds)

    if len(sys.argv) < 2:
        print("Usage: gmail.py search <query> | read <id> | send <to> <subject> <body>")
        return

    cmd = sys.argv[1]

    if cmd == "search":
        query = sys.argv[2] if len(sys.argv) > 2 else "in:inbox"
        results = service.users().messages().list(userId='me', q=query, maxResults=10).execute()
        msgs = results.get('messages', [])
        for m in msgs:
            msg = service.users().messages().get(userId='me', id=m['id'], format='metadata',
                  metadataHeaders=['From','Subject','Date']).execute()
            headers = {h['name']: h['value'] for h in msg['payload']['headers']}
            print(f"[{m['id']}] {headers.get('Date','?')[:16]} | {headers.get('From','?')[:30]} | {headers.get('Subject','?')[:50]}")

    elif cmd == "read":
        msg_id = sys.argv[2]
        msg    = service.users().messages().get(userId='me', id=msg_id, format='full').execute()
        payload = msg['payload']
        body = ""
        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    body = base64.urlsafe_b64decode(part['body']['data']).decode(errors='ignore')
                    break
        elif 'body' in payload and 'data' in payload['body']:
            body = base64.urlsafe_b64decode(payload['body']['data']).decode(errors='ignore')
        headers = {h['name']: h['value'] for h in payload['headers']}
        print(f"From: {headers.get('From','?')}")
        print(f"Subject: {headers.get('Subject','?')}")
        print(f"Date: {headers.get('Date','?')}")
        print("---")
        print(body[:2000])

    elif cmd == "send":
        to, subject, body = sys.argv[2], sys.argv[3], sys.argv[4]
        import email.mime.text
        msg = email.mime.text.MIMEText(body)
        msg['to'] = to; msg['subject'] = subject
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        service.users().messages().send(userId='me', body={'raw': raw}).execute()
        print(f"✅ Sent to {to}")

if __name__ == "__main__":
    main()
