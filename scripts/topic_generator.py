#!/usr/bin/env python3
"""Deterministic topic generator and entropy calculator for igloo-notify.

Ensures zero-token execution and strict alphanumeric hygiene.
"""
from __future__ import annotations

import math
import re
import secrets
import string

ALPHANUMERIC_CHARS = string.ascii_letters + string.digits
STRICT_ALPHANUMERIC_PATTERN = re.compile(r"^[A-Za-z0-9]+\Z")


def generate_alphanumeric_suffix(length: int = 8) -> str:
    """Generate a cryptographically secure, strictly alphanumeric string.
    
    Guaranteed zero external LLM token consumption and strictly bounded to [A-Za-z0-9].
    """
    if length < 1:
        raise ValueError("Length must be at least 1")
    suffix = "".join(secrets.choice(ALPHANUMERIC_CHARS) for _ in range(length))
    if not STRICT_ALPHANUMERIC_PATTERN.fullmatch(suffix):
        raise ValueError(f"Generated string contained illegal characters: {suffix}")
    return suffix


def generate_topic(project_prefix: str, length: int = 8) -> str:
    """Combine a sanitized project name with an alphanumeric suffix."""
    sanitized_prefix = re.sub(r"[^A-Za-z0-9_-]", "-", project_prefix).strip("-")
    suffix = generate_alphanumeric_suffix(length)
    return f"{sanitized_prefix}-{suffix}"


def calculate_entropy(length: int, guesses_per_second: float = 1e8) -> dict:
    """Calculate entropy in bits and estimated brute-force duration on an average computer.
    
    Assumes standard base62 alphabet (62 possible characters).
    """
    alphabet_size = len(ALPHANUMERIC_CHARS)  # 62
    combinations = alphabet_size ** length
    entropy_bits = length * math.log2(alphabet_size)
    seconds_to_crack = combinations / guesses_per_second

    # Format human-readable duration
    if seconds_to_crack < 60:
        duration_str = f"{seconds_to_crack:.2f} seconds"
    elif seconds_to_crack < 3600:
        duration_str = f"{seconds_to_crack / 60:.1f} minutes"
    elif seconds_to_crack < 86400:
        duration_str = f"{seconds_to_crack / 3600:.1f} hours"
    elif seconds_to_crack < 31536000:
        duration_str = f"{seconds_to_crack / 86400:.1f} days"
    else:
        duration_str = f"{seconds_to_crack / 31536000:.1f} years"

    return {
        "length": length,
        "alphabet_size": alphabet_size,
        "combinations": combinations,
        "entropy_bits": round(entropy_bits, 2),
        "estimated_crack_seconds": seconds_to_crack,
        "estimated_crack_duration": duration_str,
    }
