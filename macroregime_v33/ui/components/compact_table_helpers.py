from __future__ import annotations


def compact_rows(rows: list[dict], limit: int = 15) -> list[dict]:
    return rows[:limit]


def frame_height(n_rows: int, base: int = 58, row: int = 35, max_height: int = 420) -> int:
    n = max(1, int(n_rows or 0))
    return min(max_height, base + row * n)
