#!/usr/bin/env python3
"""Unit and integration test verifying round-trip receipt of messages from ntfy.sh."""

import json
from pathlib import Path
import sys
import time
import unittest
import urllib.parse
import urllib.request

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from topic_generator import generate_topic
from remote_bridge import BridgeListener


class TestNtfyMessageReceipt(unittest.TestCase):
    """Test dispatching and receiving messages from ntfy.sh end-to-end."""

    def test_end_to_end_message_receipt(self):
        # 1. Generate an isolated ephemeral test topic
        test_topic = generate_topic("igloo-test-receipt", length=8)
        test_payload = f"Integration test payload verification at {time.time()}"

        # 2. Dispatch a user-style message (without bot robot tags) directly to ntfy.sh
        post_url = f"https://ntfy.sh/{test_topic}"
        req = urllib.request.Request(
            post_url,
            data=test_payload.encode("utf-8"),
            headers={"User-Agent": "igloo-notify-test/1.0"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            post_result = json.loads(resp.read().decode("utf-8"))
            sent_msg_id = post_result.get("id")

        self.assertIsNotNone(sent_msg_id, "ntfy.sh should return a message ID upon publishing")

        # 3. Poll ntfy.sh to verify message receipt (using since=10m)
        time.sleep(0.5)
        poll_url = f"https://ntfy.sh/{test_topic}/json?poll=1&since=10m"
        poll_req = urllib.request.Request(
            poll_url,
            headers={"User-Agent": "igloo-notify-test/1.0"},
        )

        received_messages = []
        with urllib.request.urlopen(poll_req, timeout=15) as resp:
            for line in resp:
                line_str = line.decode("utf-8").strip()
                if not line_str:
                    continue
                try:
                    event = json.loads(line_str)
                    if event.get("event") == "message":
                        received_messages.append(event)
                except json.JSONDecodeError:
                    continue

        # 4. Verify message content and listener classification
        self.assertGreaterEqual(len(received_messages), 1, "Should receive at least one message from topic")
        received_event = received_messages[-1]

        self.assertEqual(received_event.get("id"), sent_msg_id)
        self.assertEqual(received_event.get("message"), test_payload)

        # 5. Verify BridgeListener correctly identifies it as a genuine user message (not bot)
        listener = BridgeListener(topic=test_topic, state_dir=Path("/tmp/igloo_test_receipt"))
        self.assertFalse(listener.is_bot_message(received_event), "User message must not be flagged as bot message")


if __name__ == "__main__":
    unittest.main()
