"""
GoBP Description Pyramid.

Auto-extracts L1/L2 from full description text khi import node.
AI không cần làm gì — system tự extract.

L1 (~15 tokens): câu đầu tiên, max 100 chars
L2 (~40 tokens): 2-3 câu đầu, max 300 chars
L3: full text (không extract — lưu nguyên)
"""

from __future__ import annotations

import re
from typing import Any


def extract_pyramid(full_text: str) -> tuple[str, str]:
    """
    Extract L1 và L2 từ full description text.

    Args:
        full_text: Full description string

    Returns:
        (l1, l2) tuple
        l1: headline — câu đầu tiên, max 100 chars
        l2: context  — 2-3 câu đầu, max 300 chars

    Examples:
        >>> extract_pyramid("PaymentService handles transactions. Validates balance. SLA: p99 < 300ms.")
        ("PaymentService handles transactions.", "PaymentService handles transactions. Validates balance.")
    """
    if not full_text or not full_text.strip():
        return "", ""

    text = full_text.strip()

    # Tách theo câu (., !, ?)
    sentences = [
        s.strip()
        for s in re.split(r"(?<=[.!?])\s+", text)
        if s.strip()
    ]

    if not sentences:
        # Không có câu hoàn chỉnh — dùng toàn bộ text (cắt ngắn)
        l1 = text[:100]
        l2 = text[:300]
        return l1, l2

    # L1: câu đầu tiên, max 100 chars
    l1 = sentences[0][:100]

    # L2: 2-3 câu đầu, max 300 chars
    l2 = " ".join(sentences[:3])[:300]

    return l1, l2


def pyramid_from_node(node: dict[str, Any]) -> tuple[str, str]:
    """
    Extract pyramid từ node dict.
    Handles cả plain text và {info, code} format cũ.

    Args:
        node: Node dict với description field

    Returns:
        (l1, l2) tuple
    """
    desc = node.get("description", "")

    # Schema v3: description là plain text
    if isinstance(desc, str):
        return extract_pyramid(desc)

    # Schema v2 compat: description = {info, code}
    if isinstance(desc, dict):
        info = desc.get("info", "") or ""
        return extract_pyramid(info)

    return "", ""
