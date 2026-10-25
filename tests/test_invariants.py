#!/usr/bin/env python3
"""Tests for zero-token invariant, strict alphanumeric hygiene, and entropy calculations."""

import ast
from pathlib import Path
import re
import sys
import unittest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from topic_generator import (
    generate_alphanumeric_suffix,
    generate_topic,
    calculate_entropy,
    STRICT_ALPHANUMERIC_PATTERN,
)


class TestZeroTokenInvariant(unittest.TestCase):
    """Verify that no scripts import or execute LLM token-consuming dependencies."""

    FORBIDDEN_MODULES = {
        "openai",
        "anthropic",
        "google.genai",
        "google.generativeai",
        "openrouter",
        "langchain",
        "litellm",
        "transformers",
    }

    def test_scripts_are_deterministic_and_token_free(self):
        script_files = list(SCRIPTS_DIR.glob("*.py"))
        self.assertGreater(len(script_files), 0, "No script files found to audit")

        for script_path in script_files:
            content = script_path.read_text(encoding="utf-8")
            tree = ast.parse(content, filename=str(script_path))

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        base_mod = alias.name.split(".")[0]
                        self.assertNotIn(
                            base_mod,
                            self.FORBIDDEN_MODULES,
                            f"Prohibited LLM token-consuming library '{alias.name}' imported in {script_path.name}",
                        )
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        base_mod = node.module.split(".")[0]
                        self.assertNotIn(
                            base_mod,
                            self.FORBIDDEN_MODULES,
                            f"Prohibited LLM token-consuming library '{node.module}' imported in {script_path.name}",
                        )


class TestAlphanumericHygiene(unittest.TestCase):
    """Verify alphanumeric generator produces clean strings with zero stray characters."""

    FORBIDDEN_CHARACTERS = set("'\"=!/@#$%^&*()[]{}:;,.?<>\\|`~ \t\n\r")

    def test_generated_lengths(self):
        for length in (4, 6, 8, 12):
            suffix = generate_alphanumeric_suffix(length)
            self.assertEqual(len(suffix), length)
            self.assertTrue(STRICT_ALPHANUMERIC_PATTERN.fullmatch(suffix))
            self.assertFalse(any(c in self.FORBIDDEN_CHARACTERS for c in suffix))

    def test_mass_generation_no_stray_characters(self):
        # Generate 1,000 samples to verify statistical hygiene
        for _ in range(1000):
            suffix = generate_alphanumeric_suffix(8)
            self.assertTrue(STRICT_ALPHANUMERIC_PATTERN.fullmatch(suffix))
            self.assertTrue(set(suffix).isdisjoint(self.FORBIDDEN_CHARACTERS))

    def test_project_topic_formatting(self):
        topic = generate_topic("igloo-notify", length=6)
        self.assertTrue(topic.startswith("igloo-notify-"))
        suffix = topic.split("igloo-notify-")[1]
        self.assertEqual(len(suffix), 6)
        self.assertTrue(STRICT_ALPHANUMERIC_PATTERN.fullmatch(suffix))


class TestEntropyCalculations(unittest.TestCase):
    """Verify entropy in bits and estimated crack times across key lengths."""

    def test_entropy_bits(self):
        # Base62 single character is ~5.954 bits
        res_4 = calculate_entropy(4)
        self.assertAlmostEqual(res_4["entropy_bits"], 23.82, places=1)

        res_6 = calculate_entropy(6)
        self.assertAlmostEqual(res_6["entropy_bits"], 35.73, places=1)

        res_8 = calculate_entropy(8)
        self.assertAlmostEqual(res_8["entropy_bits"], 47.63, places=1)

        res_12 = calculate_entropy(12)
        self.assertAlmostEqual(res_12["entropy_bits"], 71.45, places=1)

    def test_crack_duration_output(self):
        res = calculate_entropy(8)
        self.assertIn("estimated_crack_duration", res)
        self.assertIsInstance(res["estimated_crack_duration"], str)


if __name__ == "__main__":
    unittest.main()
