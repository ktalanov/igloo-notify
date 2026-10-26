#!/usr/bin/env python3
"""Bidirectional ntfy remote bridge daemon for igloo-notify.

Subscribes to live streaming events from the configured ntfy topic.
Deduplicates messages, suppresses bot reflection loops, and emits inbound
user messages to stdout for reactive agent ingestion.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import signal
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

from lifecycle import lifecycle_session

TOPIC_PATTERN = re.compile(
    r"^(?:[A-Za-z0-9_-]{1,64}|[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})\Z"
)


def resolve_topic(override: str | None = None, root: Path | None = None) -> str:
    if override:
        cleaned = override.strip().strip("'\"")
        if TOPIC_PATTERN.fullmatch(cleaned):
            return cleaned

    # 1. Environment variables
    for var in ("NTFY_TOPIC", "NTFY-TOPIC", "NTFY_REMOTE_TOPIC", "NTFY-REMOTE-TOPIC"):
        val = os.environ.get(var)
        if val:
            cleaned = val.strip().strip("'\"")
            if TOPIC_PATTERN.fullmatch(cleaned):
                return cleaned

    # 2. Target root .env
    target_root = Path(root or Path.cwd()).resolve()
    dotenv = target_root / ".env"
    if dotenv.is_file():
        try:
            content = dotenv.read_text(encoding="utf-8")
            for match in re.finditer(r"^\s*(?:export\s+)?([A-Za-z0-9_-]+[-_]NOTIFY)\s*=\s*['\"]?([^\s'\"#]+)", content, re.MULTILINE):
                candidate = match.group(2).strip()
                if TOPIC_PATTERN.fullmatch(candidate):
                    return candidate
        except OSError:
            pass

    # 3. User secrets ~/.env.secrets
    secrets_path = Path.home() / ".env.secrets"
    if secrets_path.is_file():
        try:
            content = secrets_path.read_text(encoding="utf-8")
            match = re.search(r"NTFY[-_]REMOTE[-_]TOPIC\s*=\s*['\"]?([^\s'\"#]+)", content)
            if match:
                candidate = match.group(1).strip()
                if TOPIC_PATTERN.fullmatch(candidate):
                    return candidate
        except OSError:
            pass

    # Default fallback
    return "vonalato"


# Pattern matching sensitive credentials, tokens, or passwords
SENSITIVE_PATTERN = re.compile(
    r"(?i)\b(?:password|passwd|pwd|private[_-]?key)\b|\b(?:api[_-]?key|bearer\s+[A-Za-z0-9_\-\.]+|auth[_-]?token)\b"
)


def contains_sensitive_content(text: str) -> bool:
    """Detect if an inbound message appears to contain passwords or credentials."""
    return bool(SENSITIVE_PATTERN.search(text))


def format_ntfy_chat_echo(body: str) -> str:
    """Format inbound ntfy text verbatim for the chat stream."""
    return f"**User NTFY received:** {body}"


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


def acknowledge_ntfy(topic: str, subject: str, is_sensitive: bool = False) -> dict:
    """Dispatch immediate standardized receipt confirmation back to user on topic."""
    url = f"https://ntfy.sh/{topic}"
    if is_sensitive:
        ack_message = (
            "⚠️ Credentials submitted over remote topic are strictly prohibited. "
            "Message rejected per security policy; please delete immediately."
        )
        headers = {
            "Title": "[Aggs] Security Alert: Credential Rejected",
            "Tags": "warning,no_entry",
            "Priority": "4",
            "User-Agent": "igloo-notify-bridge/1.0",
        }
    else:
        ack_message = f"Got your message about {subject}!"
        headers = {
            "Title": "[Aggs] Receipt Acknowledged",
            "Tags": "robot,white_check_mark",
            "Priority": "3",
            "User-Agent": "igloo-notify-bridge/1.0",
        }
    req = urllib.request.Request(url, data=ack_message.encode("utf-8"), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return {"error": str(e), "status": "failed"}


class BridgeListener:
    def __init__(
        self,
        topic: str,
        state_dir: Path | None = None,
        once: bool = False,
        auto_ack: bool = False,
        scope: str = "full",
    ):
        self.topic = topic
        self.state_dir = Path(state_dir or (Path.home() / ".cache" / "igloo-notify")).resolve()
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.seen_file = self.state_dir / f"seen_{self.topic}.txt"
        self.seen_ids = self._load_seen()
        self._running = True
        self.once = once
        self.auto_ack = auto_ack
        self.scope = scope.lower().strip()

    def _load_seen(self) -> set[str]:
        if self.seen_file.is_file():
            try:
                return set(line.strip() for line in self.seen_file.read_text(encoding="utf-8").splitlines() if line.strip())
            except OSError:
                pass
        return set()

    def record_seen(self, msg_id: str) -> None:
        self.seen_ids.add(msg_id)
        try:
            with open(self.seen_file, "a", encoding="utf-8") as f:
                f.write(f"{msg_id}\n")
        except OSError:
            pass

    def stop(self, *args) -> None:
        self._running = False
        print(f"\n[*] Bridge listener on '{self.topic}' stopping...", flush=True)

    def is_bot_message(self, event: dict) -> bool:
        tags = event.get("tags") or []
        title = event.get("title") or ""
        # Check standard bot identifiers
        if "robot" in tags or "bot" in tags or "sparkles" in tags:
            return True
        if title.startswith("[Aggs]") or title.startswith("[Agent]") or "Aggs" in title:
            return True
        return False

    def run(self) -> int:
        stream_url = f"https://ntfy.sh/{self.topic}/json?since=latest"
        backoff = 2

        print(f"[*] Starting ntfy bridge listener on topic: {self.topic}", flush=True)
        print(f"[*] State cache: {self.seen_file}", flush=True)

        signal.signal(signal.SIGINT, self.stop)
        signal.signal(signal.SIGTERM, self.stop)

        with lifecycle_session(self.topic):
            while self._running:
                try:
                    req = urllib.request.Request(
                        stream_url,
                        headers={"User-Agent": "igloo-notify-bridge/1.0"},
                    )
                    with urllib.request.urlopen(req, timeout=90) as response:
                        print(f"[+] Connected to live event stream on {self.topic}", flush=True)
                        backoff = 2

                        for line in response:
                            if not self._running:
                                break
                            line_str = line.decode("utf-8").strip()
                            if not line_str:
                                continue
                            try:
                                event = json.loads(line_str)
                            except json.JSONDecodeError:
                                continue

                            if event.get("event") != "message":
                                continue

                            msg_id = event.get("id")
                            if msg_id and msg_id in self.seen_ids:
                                continue

                            if self.is_bot_message(event):
                                if msg_id:
                                    self.record_seen(msg_id)
                                continue

                            if msg_id:
                                self.record_seen(msg_id)

                            msg_text = event.get("message", "")
                            timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
                            is_sensitive = contains_sensitive_content(msg_text)
                            subject = extract_subject(msg_text)

                            if self.auto_ack:
                                acknowledge_ntfy(self.topic, subject, is_sensitive=is_sensitive)

                            if is_sensitive:
                                # Reject credentials; do not elevate or echo raw credential
                                print(
                                    f"\n======================================================================\n"
                                    f"🚨 [REJECTED CREDENTIAL PAYLOAD] 🚨\n"
                                    f"Topic: {self.topic}\n"
                                    f"Time:  {timestamp}\n"
                                    f"ID:    {msg_id}\n"
                                    f"Status: REJECTED\n"
                                    f"----------------------------------------------------------------------\n"
                                    f"Security Boundary Violation: Inbound message contained passwords/credentials.\n"
                                    f"Payload discarded. Remote user notified to delete message immediately.\n"
                                    f"======================================================================\n",
                                    flush=True,
                                )
                            else:
                                # Print clean delimited record for the agent harness with verbatim echo
                                print(
                                    f"\n======================================================================\n"
                                    f"🚨 [REMOTE NTFY USER INPUT] 🚨\n"
                                    f"Topic: {self.topic}\n"
                                    f"Time:  {timestamp}\n"
                                    f"ID:    {msg_id}\n"
                                    f"Subject: {subject}\n"
                                    f"Scope: {self.scope}\n"
                                    f"----------------------------------------------------------------------\n"
                                    f"{format_ntfy_chat_echo(msg_text)}\n"
                                    f"======================================================================\n",
                                    flush=True,
                                )
                            if self.once:
                                self._running = False
                                break
                except (urllib.error.URLError, TimeoutError, OSError) as err:
                    if not self._running:
                        break
                    print(f"[!] Stream disconnected ({err}), reconnecting in {backoff}s...", flush=True)
                    time.sleep(backoff)
                    backoff = min(backoff * 2, 30)

        return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--topic", help="Topic override (defaults to environment or vonalato)")
    parser.add_argument("--root", type=Path, help="Target repository root")
    parser.add_argument("--state-dir", type=Path, help="State directory for deduplication log")
    parser.add_argument("--once", action="store_true", help="Exit immediately after receiving one message")
    parser.add_argument("--auto-ack", action="store_true", help="Automatically acknowledge incoming message on topic with 'Got your message about {subject}!'")
    parser.add_argument("--scope", choices=["full", "restricted"], default="full", help="Scope of accepted input: full (all instructions) or restricted (answers/approvals only)")
    args = parser.parse_args()

    topic = resolve_topic(args.topic, root=args.root)
    listener = BridgeListener(topic, state_dir=args.state_dir, once=args.once, auto_ack=args.auto_ack, scope=args.scope)
    return listener.run()


if __name__ == "__main__":
    sys.exit(main())
