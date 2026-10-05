"""Deterministic text chunking with overlap."""

from __future__ import annotations

import re


def chunks(text: str, size: int = 1_200, overlap: int = 200) -> list[str]:
    if size <= 0 or overlap < 0 or overlap >= size:
        raise ValueError("chunk_size must be positive and overlap must be in [0, chunk_size)")
    clean = re.sub(r"[ \t]+", " ", text).strip()
    if not clean:
        return []
    result: list[str] = []
    start = 0
    while start < len(clean):
        end = min(start + size, len(clean))
        if end < len(clean):
            boundary = max(clean.rfind("\n", start, end), clean.rfind(". ", start, end))
            if boundary > start + size // 2:
                end = boundary + 1
        result.append(clean[start:end].strip())
        if end == len(clean):
            break
        start = end - overlap
    return result

