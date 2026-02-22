"""
PII Filter — Scrubs sensitive data before sending to LLMs.
Filters: emails, IPs, phone numbers, SSNs, API keys/tokens.
"""

import re
from typing import List, Tuple

# Patterns: (regex, replacement label)
PII_PATTERNS: List[Tuple[re.Pattern, str]] = [
    (re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'), '[EMAIL_REDACTED]'),
    (re.compile(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b'), '[IP_REDACTED]'),
    (re.compile(r'\b\d{3}[-.\s]?\d{2}[-.\s]?\d{4}\b'), '[SSN_REDACTED]'),
    (re.compile(r'\b(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b'), '[PHONE_REDACTED]'),
    (re.compile(r'\b(ghp_[A-Za-z0-9_]{36,})\b'), '[GITHUB_TOKEN_REDACTED]'),
    (re.compile(r'\b(sk-[A-Za-z0-9]{32,})\b'), '[API_KEY_REDACTED]'),
    (re.compile(r'\b(xox[bpsa]-[A-Za-z0-9-]+)\b'), '[SLACK_TOKEN_REDACTED]'),
]


def filter_pii(text: str) -> str:
    """Scrub all PII patterns from text."""
    if not text:
        return text
    for pattern, replacement in PII_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def filter_state_pii(state: dict) -> dict:
    """Apply PII filter to relevant fields in the incident state."""
    filtered = dict(state)
    if "raw_description" in filtered:
        filtered["raw_description"] = filter_pii(filtered["raw_description"])
    if "root_cause_analysis" in filtered:
        filtered["root_cause_analysis"] = filter_pii(filtered["root_cause_analysis"])
    if "suggested_resolution" in filtered:
        filtered["suggested_resolution"] = filter_pii(filtered["suggested_resolution"])
    return filtered
