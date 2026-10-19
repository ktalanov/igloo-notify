#!/usr/bin/env python3
"""Outbound notification dispatcher CLI for igloo-notify.

Dispatches structured notifications to ntfy.sh topics following the Igloo
notification standards, with automatic topic resolution, tag mapping,
and priority normalization.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import sys
import urllib.error
import urllib.request

from remote_bridge import resolve_topic, TOPIC_PATTERN

SEVERITY_MAP = {
    "progress": {"priority": 2, "default_tags": "hourglass_flowing_sand"},
    "normal": {"priority": 3, "default_tags": "information_source"},
    "warning": {"priority": 4, "default_tags": "warning"},
    "urgent": {"priority": 5, "default_tags": "rotating_light"},
    "P3": {"priority": 3, "default_tags": "information_source"},
    "P2": {"priority": 3, "default_tags": "information_source"},
    "P1": {"priority": 4, "default_tags": "warning"},
    "P0": {"priority": 5, "default_tags": "rotating_light"},
}


def send_notification(
    message: str,
    title: str = "[Aggs] Milestone",
    severity: str = "normal",
    tags: str | None = None,
    topic: str | None = None,
    evidence: str | None = None,
    root: Path | None = None,
    dry_run: bool = False,
) -> dict:
    target_topic = resolve_topic(topic, root=root)
    sev_info = SEVERITY_MAP.get(severity, SEVERITY_MAP["normal"])
    priority_num = sev_info["priority"]
    final_tags = tags or sev_info["default_tags"]
    # Ensure robot tag is included for reflection loop filtering
    tag_list = [t.strip() for t in final_tags.split(",") if t.strip()]
    if "robot" not in tag_list:
        tag_list.append("robot")
    merged_tags = ",".join(tag_list)

    body = message
    if evidence:
        body = f"{message}\n\nEvidence: {evidence}"

    result = {
        "topic": target_topic,
        "title": title,
        "severity": severity,
        "priority": priority_num,
        "tags": tag_list,
        "status": "dry-run" if dry_run else "pending",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    if dry_run:
        return result

    url = f"https://ntfy.sh/{target_topic}"
    headers = {
        "Title": title,
        "Tags": merged_tags,
        "Priority": str(priority_num),
        "User-Agent": "igloo-notify/1.0",
    }
    req = urllib.request.Request(url, data=body.encode("utf-8"), headers=headers, method="POST")

    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                result["status"] = "delivered"
                result["id"] = data.get("id")
                return result
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as err:
            if attempt == 2:
                result["status"] = "failed"
                result["error"] = str(err)
                return result

    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--message", "-m", required=True, help="Notification body text")
    parser.add_argument("--title", "-t", default="[Aggs] Terminal Milestone", help="Notification title")
    parser.add_argument(
        "--severity",
        "-s",
        choices=("progress", "normal", "warning", "urgent", "P0", "P1", "P2", "P3"),
        default="normal",
        help="Severity rating",
    )
    parser.add_argument("--tags", help="Comma-separated emoji or tags (e.g. 'rocket,white_check_mark')")
    parser.add_argument("--topic", help="Destination ntfy topic override")
    parser.add_argument("--evidence", help="Evidence URL or local file link")
    parser.add_argument("--root", type=Path, help="Target project root for .env resolution")
    parser.add_argument("--dry-run", action="store_true", help="Format and print event without sending")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON")

    args = parser.parse_args()

    res = send_notification(
        message=args.message,
        title=args.title,
        severity=args.severity,
        tags=args.tags,
        topic=args.topic,
        evidence=args.evidence,
        root=args.root,
        dry_run=args.dry_run,
    )

    if args.json:
        print(json.dumps(res, indent=2))
    else:
        status_icon = "✓" if res["status"] in ("delivered", "dry-run") else "✗"
        print(f"[{status_icon}] {res['status'].upper()}: {res['title']} -> ntfy.sh/{res['topic']}")
        if "id" in res:
            print(f"    ID: {res['id']}")
        if "error" in res:
            print(f"    Error: {res['error']}", file=sys.stderr)

    return 0 if res["status"] in ("delivered", "dry-run") else 1


if __name__ == "__main__":
    sys.exit(main())
