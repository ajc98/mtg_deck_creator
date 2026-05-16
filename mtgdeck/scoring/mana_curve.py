"""Mana curve analysis helpers."""
from __future__ import annotations

from collections import Counter


def curve_counts(cmcs: list[float]) -> dict[int, int]:
    """Return a histogram of mana values (bucketing 7+ together)."""
    c: Counter[int] = Counter()
    for cmc in cmcs:
        bucket = min(int(cmc), 7)
        c[bucket] += 1
    return dict(sorted(c.items()))


def average_cmc(cmcs: list[float]) -> float:
    non_land = [c for c in cmcs if c > 0]
    return sum(non_land) / len(non_land) if non_land else 0.0


def curve_health(cmcs: list[float]) -> dict:
    """Return a brief assessment of the mana curve."""
    counts = curve_counts(cmcs)
    avg = average_cmc(cmcs)
    total = len(cmcs)
    warnings: list[str] = []

    two_three = counts.get(2, 0) + counts.get(3, 0)
    if total > 0 and two_three / total < 0.20:
        warnings.append("Low 2–3 drop count; consider more early plays.")

    high_end = sum(v for k, v in counts.items() if k >= 6)
    if total > 0 and high_end / total > 0.20:
        warnings.append("Many 6+ CMC spells; curve may be too top-heavy.")

    if avg > 4.0:
        warnings.append(f"High average CMC ({avg:.1f}); expect slower games.")

    return {
        "counts": counts,
        "average": round(avg, 2),
        "warnings": warnings,
    }
