#!/usr/bin/env python3
"""Twilio SMS bridge for igloo-notify.

Sends status queries to the user's phone and polls for inbound SMS replies,
elevating them as direct user commands.
"""
from __future__ import annotations

import argparse
import base64
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

STATE_DIR = Path.home() / ".cache" / "igloo-notify"
SEEN_FILE = STATE_DIR / "seen_sms.txt"


def get_twilio_credentials() -> tuple[str, str, str, str]:
    sid = os.environ.get("TWILIO_ACCOUNT_SID")
    token = os.environ.get("TWILIO_AUTH_TOKEN")
    from_num = os.environ.get("TWILIO_PHONE_NUMBER")
    to_num = os.environ.get("MY_PHONE_NUMBER")

    if not all([sid, token, from_num, to_num]):
        secrets_file = Path.home() / ".env.secrets"
        if secrets_file.is_file():
            for line in secrets_file.read_text(encoding="utf-8").splitlines():
                if "=" in line and not line.strip().startswith("#"):
                    k, v = line.strip().split("=", 1)
                    k = k.replace("export", "").strip()
                    v = v.strip().strip("'\"")
                    if k == "TWILIO_ACCOUNT_SID" and not sid:
                        sid = v
                    elif k == "TWILIO_AUTH_TOKEN" and not token:
                        token = v
                    elif k == "TWILIO_PHONE_NUMBER" and not from_num:
                        from_num = v
                    elif k == "MY_PHONE_NUMBER" and not to_num:
                        to_num = v

    if not (sid and token and from_num and to_num):
        raise ValueError("Missing Twilio credentials or phone numbers")

    # Format numbers with +
    if not from_num.startswith("+"):
        from_num = f"+{from_num}"
    if not to_num.startswith("+"):
        to_num = f"+{to_num}"

    return sid, token, from_num, to_num


def send_sms(body: str) -> dict:
    sid, token, from_num, to_num = get_twilio_credentials()
    url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"
    data = urllib.parse.urlencode({
        "To": to_num,
        "From": from_num,
        "Body": body,
    }).encode("utf-8")

    auth_header = base64.b64encode(f"{sid}:{token}".encode("utf-8")).decode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Authorization": f"Basic {auth_header}",
            "User-Agent": "igloo-sms-bridge/1.0",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


# Pattern matching sensitive credentials, tokens, or passwords
SENSITIVE_PATTERN = re.compile(
    r"(?i)\b(?:password|passwd|pwd|private[_-]?key)\b|\b(?:api[_-]?key|bearer\s+[A-Za-z0-9_\-\.]+|auth[_-]?token)\b"
)


def contains_sensitive_content(text: str) -> bool:
    """Detect if an inbound message appears to contain passwords or credentials."""
    return bool(SENSITIVE_PATTERN.search(text))


def format_sms_chat_echo(body: str) -> str:
    """Format inbound SMS text verbatim for the chat stream."""
    return f"**User SMS received:** {body}"


def extract_subject(text: str, max_words: int = 6) -> str:
    """Extract a concise subject summary from an inbound message for acknowledgments."""
    if contains_sensitive_content(text):
        return "[sensitive content redacted]"

    cleaned = " ".join(text.strip().split())
    if not cleaned:
        return "your update"
    words = cleaned.split()
    if len(words) <= max_words:
        subject = cleaned.rstrip(".?!,;:")
    else:
        subject = " ".join(words[:max_words]).rstrip(".?!,;:") + "..."
    return subject


def acknowledge_sms(subject: str, is_sensitive: bool = False) -> dict:
    """Send immediate standardized receipt confirmation back to user phone."""
    if is_sensitive:
        ack_body = (
            "⚠️ Credentials submitted over SMS are strictly prohibited. "
            "Message rejected per security policy; please delete immediately."
        )
    else:
        ack_body = f"Got your message about {subject}!"
    return send_sms(ack_body)


def check_inbound_sms(auto_ack: bool = False, scope: str = "full") -> list[dict]:
    sid, token, from_num, to_num = get_twilio_credentials()
    url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json?To={urllib.parse.quote(from_num)}&PageSize=10"

    auth_header = base64.b64encode(f"{sid}:{token}".encode("utf-8")).decode("utf-8")
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Basic {auth_header}",
            "User-Agent": "igloo-sms-bridge/1.0",
        },
    )

    STATE_DIR.mkdir(parents=True, exist_ok=True)
    seen_ids = set()
    if SEEN_FILE.is_file():
        seen_ids = set(line.strip() for line in SEEN_FILE.read_text(encoding="utf-8").splitlines() if line.strip())

    new_messages = []
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        messages = data.get("messages", [])
        for msg in messages:
            msg_sid = msg.get("sid")
            direction = msg.get("direction")
            sender = msg.get("from")
            body_text = msg.get("body", "")
            if direction == "inbound" and msg_sid not in seen_ids and sender == to_num:
                new_messages.append(msg)
                with open(SEEN_FILE, "a", encoding="utf-8") as f:
                    f.write(f"{msg_sid}\n")

                is_sensitive = contains_sensitive_content(body_text)
                subject = extract_subject(body_text)

                if auto_ack:
                    try:
                        acknowledge_sms(subject, is_sensitive=is_sensitive)
                    except Exception as e:
                        print(f"[!] Warning: failed to auto-acknowledge SMS {msg_sid}: {e}", file=sys.stderr)

                if is_sensitive:
                    print(
                        f"\n======================================================================\n"
                        f"🚨 [REJECTED CREDENTIAL PAYLOAD] 🚨\n"
                        f"Source: Twilio SMS ({sender})\n"
                        f"SID:    {msg_sid}\n"
                        f"Status: REJECTED\n"
                        f"----------------------------------------------------------------------\n"
                        f"Security Boundary Violation: Inbound SMS contained passwords/credentials.\n"
                        f"Payload discarded. User notified via SMS to delete message immediately.\n"
                        f"======================================================================\n",
                        flush=True,
                    )
                else:
                    print(
                        f"\n======================================================================\n"
                        f"🚨 [REMOTE SMS USER INPUT] 🚨\n"
                        f"Source: Twilio SMS ({sender})\n"
                        f"SID:    {msg_sid}\n"
                        f"Subject: {subject}\n"
                        f"Scope: {scope}\n"
                        f"----------------------------------------------------------------------\n"
                        f"{format_sms_chat_echo(body_text)}\n"
                        f"======================================================================\n",
                        flush=True,
                    )

    return new_messages


def main():
    parser = argparse.ArgumentParser(description="Twilio SMS Bridge for igloo-notify")
    parser.add_argument("--send", help="Send SMS body to user's phone")
    parser.add_argument("--check", action="store_true", help="Check for newly received SMS replies")
    parser.add_argument("--auto-ack", action="store_true", help="Automatically acknowledge incoming SMS with 'Got your message about {subject}!'")
    parser.add_argument("--query-status", action="store_true", help="Send standard 5-minute health check SMS")
    parser.add_argument("--scope", choices=["full", "restricted"], default="full", help="Scope of accepted input: full (all instructions) or restricted (answers/approvals only)")
    args = parser.parse_args()

    if args.send:
        res = send_sms(args.send)
        print(f"[✓] SMS Sent: {res.get('sid')} -> {res.get('to')}")

    if args.query_status:
        body = "Hi Talanov, this is Aggs. Did we fix it, or do we still have issues? Reply to instruct me."
        res = send_sms(body)
        print(f"[✓] Status Query SMS Sent: {res.get('sid')} -> {res.get('to')}")

    if args.check:
        new_msgs = check_inbound_sms(auto_ack=args.auto_ack, scope=args.scope)
        if not new_msgs:
            print("[*] No new inbound SMS.")


if __name__ == "__main__":
    main()
