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


class BridgeListener:
    def __init__(self, topic: str, state_dir: Path | None = None):
        self.topic = topic
        self.state_dir = Path(state_dir or (Path.home() / ".cache" / "igloo-notify")).resolve()
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.seen_file = self.state_dir / f"seen_{self.topic}.txt"
        self.seen_ids = self._load_seen()
        self._running = True

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

                            # Print clean delimited record for the agent harness
                            print(
                                f"\n======================================================================\n"
                                f"🚨 [REMOTE NTFY USER INPUT] 🚨\n"
                                f"Topic: {self.topic}\n"
                                f"Time:  {timestamp}\n"
                                f"ID:    {msg_id}\n"
                                f"----------------------------------------------------------------------\n"
                                f"{msg_text}\n"
                                f"======================================================================\n",
                                flush=True,
                            )
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
    args = parser.parse_args()

    topic = resolve_topic(args.topic, root=args.root)
    listener = BridgeListener(topic, state_dir=args.state_dir)
    return listener.run()


if __name__ == "__main__":
    sys.exit(main())
