#!/usr/bin/env python3
"""Audit lifecycle manager for igloo-notify.

Dispatches critical alert to 'vonalato' and a local desktop notify-send
warning when a task begins, and notifies both the target topic and 'vonalato'
when the task closes.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
import urllib.error
import urllib.request

AUDIT_TOPIC = "vonalato"


def detect_harness_process() -> str:
    """Detect calling harness process name (e.g. agy, codex, chatgpt)."""
    try:
        pid = os.getppid()
        while pid > 1:
            try:
                with open(f"/proc/{pid}/comm", "r", encoding="utf-8") as f:
                    comm = f.read().strip()
                if comm in ("agy", "codex", "chatgpt", "antigravity", "cursor", "vscode"):
                    return comm
                with open(f"/proc/{pid}/cmdline", "r", encoding="utf-8") as f:
                    cmdline = f.read().replace("\x00", " ").strip()
                for known in ("agy", "codex", "chatgpt", "antigravity"):
                    if known in cmdline.split():
                        return known
                with open(f"/proc/{pid}/stat", "r", encoding="utf-8") as f:
                    pid = int(f.read().split()[3])
            except (OSError, IndexError, ValueError):
                break
    except Exception:
        pass
    return "agy"


def _send_ntfy(topic: str, title: str, message: str, tags: str = "robot", priority: str = "default") -> dict:
    url = f"https://ntfy.sh/{topic}"
    headers = {
        "Title": title,
        "Tags": tags,
        "Priority": priority,
        "User-Agent": "igloo-notify-lifecycle/1.0",
    }
    req = urllib.request.Request(url, data=message.encode("utf-8"), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return {"error": str(e), "status": "failed"}


def _desktop_notify(summary: str, body: str, urgency: str = "critical") -> None:
    """Send local desktop notification via notify-send without exposing private machine details."""
    notify_send = shutil.which("notify-send")
    if not notify_send:
        return
    try:
        subprocess.run(
            [notify_send, "-u", urgency, "-a", "igloo-notify", summary, body],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=5,
        )
    except Exception:
        pass


def notify_task_start(topic_used: str, process_name: str | None = None) -> None:
    """Send critical alert to vonalato and desktop notification on task start."""
    harness = process_name or detect_harness_process()
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    # Strictly sanitize: bold, emojis, no hostnames, usernames, or paths
    ntfy_message = f"🚨 **igloo-notify task is running** and was started at **{now_str}** from **{harness}**"
    ntfy_title = "🚨 [Critical Alert] igloo-notify Running"

    # 1. Critical ntfy alert to 'vonalato'
    _send_ntfy(
        topic=AUDIT_TOPIC,
        title=ntfy_title,
        message=ntfy_message,
        tags="rotating_light,warning,robot",
        priority="5",  # Critical / Urgent priority
    )

    # 2. Local desktop warning
    desktop_body = f"igloo-notify task started at {now_str} from {harness}"
    _desktop_notify("🚨 igloo-notify Task Running", desktop_body, urgency="critical")


def notify_task_close(topic_used: str, process_name: str | None = None) -> None:
    """Send close message to both the active topic and vonalato."""
    harness = process_name or detect_harness_process()
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    close_message = f"🏁 **igloo-notify task has closed** (finished at **{now_str}** for **{harness}**)"
    close_title = "🏁 [Task Closed] igloo-notify Finished"

    # Send to active topic used
    _send_ntfy(
        topic=topic_used,
        title=close_title,
        message=close_message,
        tags="white_check_mark,robot",
        priority="3",
    )

    # Send to vonalato if different
    if topic_used != AUDIT_TOPIC:
        _send_ntfy(
            topic=AUDIT_TOPIC,
            title=close_title,
            message=close_message,
            tags="white_check_mark,robot",
            priority="3",
        )

    _desktop_notify("🏁 igloo-notify Task Closed", f"Finished at {now_str} for {harness}", urgency="normal")


@contextmanager
def lifecycle_session(topic_used: str, process_name: str | None = None):
    """Context manager for managing task start and close notifications."""
    notify_task_start(topic_used, process_name=process_name)
    try:
        yield
    finally:
        notify_task_close(topic_used, process_name=process_name)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("start", "close"))
    parser.add_argument("--topic", default="vonalato")
    args = parser.parse_args()

    if args.action == "start":
        notify_task_start(args.topic)
        print(f"[ok] Sent critical start alert to {AUDIT_TOPIC} and desktop.")
    else:
        notify_task_close(args.topic)
        print(f"[ok] Sent close notification to {args.topic} and {AUDIT_TOPIC}.")
