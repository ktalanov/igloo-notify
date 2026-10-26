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

from remote_bridge import (
    resolve_topic,
    BridgeListener,
    TOPIC_PATTERN,
    format_ntfy_chat_echo,
    extract_subject,
    acknowledge_ntfy,
)
from sms_bridge import format_sms_chat_echo, extract_subject as extract_sms_subject, acknowledge_sms
from notify_bridge import send_notification, SEVERITY_MAP
from lifecycle import detect_harness_process, notify_task_start, notify_task_close, AUDIT_TOPIC


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

    def test_once_flag_behavior(self):
        once_listener = BridgeListener(topic="test-topic", state_dir=Path("/tmp/igloo_notify_test"), once=True)
        self.assertTrue(once_listener.once)

    def test_chat_echo_formatting(self):
        ntfy_echo = format_ntfy_chat_echo("build the package now")
        self.assertEqual(ntfy_echo, "**User NTFY received:** build the package now")

        sms_echo = format_sms_chat_echo("deploy to staging server")
        self.assertEqual(sms_echo, "**User SMS received:** deploy to staging server")

    def test_extract_subject(self):
        # Concise input
        subj1 = extract_subject("deploy to staging server")
        self.assertEqual(subj1, "deploy to staging server")

        # Long input truncated to max_words with ellipsis
        subj2 = extract_subject("can you please run the integration tests across all servers right now")
        self.assertEqual(subj2, "can you please run the integration...")

        # Trailing punctuation cleaned
        subj3 = extract_subject("is the build done yet?")
        self.assertEqual(subj3, "is the build done yet")

        # Empty string fallback
        subj4 = extract_subject("   ")
        self.assertEqual(subj4, "your update")

    @patch("urllib.request.urlopen")
    def test_acknowledge_ntfy(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = b'{"id": "ack-123"}'
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        res = acknowledge_ntfy("test-topic", "deploying staging")
        self.assertTrue(mock_urlopen.called)
        req = mock_urlopen.call_args[0][0]
        self.assertIn("Got your message about deploying staging!", req.data.decode("utf-8"))
        self.assertEqual(req.headers["Title"], "[Aggs] Receipt Acknowledged")


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


class TestLifecycle(unittest.TestCase):
    def test_detect_harness_process(self):
        proc = detect_harness_process()
        self.assertIsInstance(proc, str)
        self.assertTrue(len(proc) > 0)

    @patch("lifecycle._send_ntfy")
    @patch("lifecycle._desktop_notify")
    def test_notify_task_start_format(self, mock_desktop, mock_ntfy):
        notify_task_start(topic_used="target-project-topic", process_name="agy")
        self.assertTrue(mock_ntfy.called)
        call_kwargs = mock_ntfy.call_args[1]
        self.assertEqual(call_kwargs["topic"], AUDIT_TOPIC)
        self.assertEqual(call_kwargs["priority"], "5")
        self.assertIn("igloo-notify task is running", call_kwargs["message"])
        self.assertIn("agy", call_kwargs["message"])
        # Ensure no paths or usernames are in the message
        self.assertNotIn("/home/", call_kwargs["message"])
        self.assertNotIn(os.environ.get("USER", "lenin"), call_kwargs["message"])

    @patch("lifecycle._send_ntfy")
    @patch("lifecycle._desktop_notify")
    def test_notify_task_close_dual_dispatch(self, mock_desktop, mock_ntfy):
        notify_task_close(topic_used="custom-topic-xyz", process_name="codex")
        self.assertEqual(mock_ntfy.call_count, 2)
        topics_called = [call[1]["topic"] for call in mock_ntfy.call_args_list]
        self.assertIn("custom-topic-xyz", topics_called)
        self.assertIn(AUDIT_TOPIC, topics_called)


if __name__ == "__main__":
    unittest.main()
