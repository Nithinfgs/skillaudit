"""Rough token estimation without a tokenizer dependency."""

from __future__ import annotations

import math


def estimate_tokens(text: str) -> int:
    """Estimate tokens as ~1 per 4 characters (a common rule of thumb).

    This is a heuristic, not a real tokenizer; results are approximate and
    deliberately dependency-free.
    """
    if not text:
        return 0
    return math.ceil(len(text) / 4)
