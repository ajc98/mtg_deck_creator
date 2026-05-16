"""Generate per-card explanation text for a built deck."""
from __future__ import annotations


def generate_explanation(
    commander_name: str,
    cards: list[dict],
    card_scores,      # list[CardScore]
    role_counts: dict[str, int],
    warnings: list[str],
) -> str:
    """Return a Markdown explanation of the deck."""
    score_map = {s.name: s for s in card_scores}

    lines: list[str] = [
        f"# Deck Explanation: {commander_name}",
        "",
        "## Role Breakdown",
        "",
    ]

    for role, count in sorted(role_counts.items()):
        if count:
            lines.append(f"- **{role.replace('_', ' ').title()}**: {count}")

    lines += ["", "## Cards and Reasons", ""]

    for card in cards:
        name = card.get("name", "Unknown")
        cs   = score_map.get(name)
        if cs:
            lines.append(f"### {name}  (score: {cs.final_score:.2f}  |  role: {cs.primary_role})")
            lines.append(cs.explanation)
        else:
            lines.append(f"### {name}")
        lines.append("")

    if warnings:
        lines += ["## Warnings", ""]
        for w in warnings:
            lines.append(f"- {w}")

    return "\n".join(lines)
