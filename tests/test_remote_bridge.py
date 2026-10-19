#!/usr/bin/env python3
"""Unit tests for igloo-notify bridge and dispatcher."""

import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch, MagicMock

# Ensure scripts directory is on sys.path
SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from remote_bridge import resolve_topic, BridgeListener, TOPIC_PATTERN
from notify_bridge import send_notification, SEVERITY_MAP


class TestTopicResolution(unittest.TestCase):
    def test_topic_pattern_valid(self):
        self.assertTrue(bool(TOPIC_PATTERN.fullmatch("vonalato")))
        self.assertTrue(bool(TOPIC_PATTERN.fullmatch("Igloo-Remote-Work-leninlab-a7Kp3mQx")))
        self.assertTrue(bool(TOPIC_PATTERN.fullmatch("83dc3cf9-3139-49c6-a7c6-4bfbbd5e49f6")))

    def test_topic_pattern_invalid(self):
        self.assertFalse(bool(TOPIC_PATTERN.fullmatch("invalid topic with spaces")))
        self.assertFalse(bool(TOPIC_PATTERN.fullmatch("topic/with/slashes")))
        self.assertFalse(bool(TOPIC_PATTERN.fullmatch("topic$with$symbols")))

    def test_cli_override(self):
        topic = resolve_topic(override="custom-topic-123")
        self.assertEqual(topic, "custom-topic-123")

    @patch.dict(os.environ, {"NTFY_TOPIC": "env-topic-abc"}, clear=False)
    def test_env_var_topic(self):
        topic = resolve_topic()
        self.assertEqual(topic, "env-topic-abc")


class TestBridgeListener(unittest.TestCase):
    def setUp(self):
        self.listener = BridgeListener(topic="test-topic", state_dir=Path("/tmp/igloo_notify_test"))

    def test_is_bot_message_suppression(self):
        # Bot message with robot tag
        bot_event_1 = {"id": "1", "tags": ["robot", "check"], "title": "Update"}
        self.assertTrue(self.listener.is_bot_message(bot_event_1))

        # Bot message with Aggs in title
        bot_event_2 = {"id": "2", "tags": ["info"], "title": "[Aggs] Milestone complete"}
        self.assertTrue(self.listener.is_bot_message(bot_event_2))

        # User message
        user_event = {"id": "3", "tags": [], "title": "", "message": "Proceed with deployment"}
        self.assertFalse(self.listener.is_bot_message(user_event))

    def test_seen_ids_deduplication(self):
        self.listener.record_seen("msg-unique-001")
        self.assertIn("msg-unique-001", self.listener.seen_ids)


class TestNotifyBridge(unittest.TestCase):
    def test_dry_run_formatting(self):
        res = send_notification(
            message="Test message",
            title="Smoke Test",
            severity="warning",
            topic="test-topic",
            dry_run=True,
        )
        self.assertEqual(res["status"], "dry-run")
        self.assertEqual(res["priority"], 4)
        self.assertIn("robot", res["tags"])
        self.assertEqual(res["topic"], "test-topic")


if __name__ == "__main__":
    unittest.main()
