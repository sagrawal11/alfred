"""
Utility helpers for nutrition pipeline.
"""

from __future__ import annotations

import re
from typing import Optional


_ws_re = re.compile(r"\s+")


def normalize_query(text: str) -> str:
    return _ws_re.sub(" ", (text or "").strip().lower())


def normalize_restaurant(text: Optional[str]) -> Optional[str]:
    t = normalize_query(text or "")
    return t or None

