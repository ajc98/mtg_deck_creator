"""Hybrid card scoring: EDHREC + vector similarity + role need + curve."""
from __future__ import annotations

from dataclasses import dataclass

# EDHREC section importance weights (0–1)
_SECTION_IMPORTANCE: dict[str, float] = {
    "synergy":       1.00,
    "mana":          0.90,
    "top":           0.85,
    "utility-lands": 0.75,
    "new":           0.65,
    "creatures":     0.60,
    "instants":      0.60,
    "sorceries":     0.60,
    "artifacts":     0.60,
    "enchantments":  0.60,
    "planeswalkers": 0.60,
    "lands":         0.60,
}


@dataclass
class ScoreWeights:
    edhrec:    float = 0.30
    vector:    float = 0.20
    role_need: float = 0.25
    synergy:   float = 0.15
    curve:     float = 0.10

    def without_vector(self) -> "ScoreWeights":
        """Redistribute vector weight when embeddings are unavailable."""
        return ScoreWeights(edhrec=0.40, vector=0.0, role_need=0.30, synergy=0.20, curve=0.10)


@dataclass
class CardScore:
    normalized_name: str
    name: str
    roles: list[str]
    primary_role: str
    edhrec_score: float
    vector_score: float
    role_need_score: float
    synergy_score: float
    curve_score: float
    final_score: float
    explanation: str


# ── Component scorers ────────────────────────────────────────────────────────


def compute_edhrec_score(rec: dict | None) -> float:
    """Combine deck %, synergy score, and section into a 0–1 signal."""
    if rec is None:
        return 0.0

    deck_pct  = float(rec.get("deck_percentage") or 0.0)
    synergy   = float(rec.get("synergy_score") or 0.0)
    section   = str(rec.get("section") or "")

    pct_norm  = min(deck_pct / 100.0, 1.0)
    # synergy is typically –1..1; map to 0–1
    syn_norm  = max(0.0, min((synergy + 1.0) / 2.0, 1.0))
    sec_score = _SECTION_IMPORTANCE.get(section, 0.55)

    return round(0.60 * pct_norm + 0.30 * syn_norm + 0.10 * sec_score, 4)


def compute_role_need_score(
    roles: list[str],
    current_counts: dict[str, int],
    targets: dict[str, int],
) -> float:
    """How urgently is this card's role needed? Returns 0–1."""
    best = 0.0
    for role in roles:
        target = targets.get(role, 0)
        if target > 0:
            current = current_counts.get(role, 0)
            need = max(0.0, (target - current) / target)
            best = max(best, need)
    return round(best, 4)


def compute_curve_score(cmc: float) -> float:
    """Prefer 2–3 CMC cards; penalize extremes. Returns 0–1."""
    if cmc <= 0:  # lands, 0-cost rocks
        return 0.50
    if 2 <= cmc <= 3:
        return 1.00
    if cmc == 1:
        return 0.80
    if cmc == 4:
        return 0.65
    if cmc == 5:
        return 0.40
    if cmc == 6:
        return 0.20
    return 0.10  # cmc >= 7


# ── Main scorer ──────────────────────────────────────────────────────────────


def score_card(
    candidate,                       # CandidateCard
    current_role_counts: dict[str, int],
    role_targets: dict[str, int],
    weights: ScoreWeights,
) -> CardScore:
    from mtgdeck.scoring.role_classifier import primary_role as get_primary

    card   = candidate.card_row
    roles  = candidate.roles
    rec    = candidate.edhrec_rec
    vscore = candidate.vector_score

    edhrec    = compute_edhrec_score(rec)
    role_need = compute_role_need_score(roles, current_role_counts, role_targets)
    curve     = compute_curve_score(float(card.get("cmc") or 0.0))
    synergy   = edhrec * 0.6 + vscore * 0.4

    # Use adjusted weights when no vector scores available
    w = weights if vscore > 0 else weights.without_vector()

    final = (
        w.edhrec    * edhrec
        + w.vector    * vscore
        + w.role_need * role_need
        + w.synergy   * synergy
        + w.curve     * curve
    )

    # Build human-readable explanation
    parts: list[str] = []
    if rec:
        pct = rec.get("deck_percentage") or 0
        parts.append(f"EDHREC {pct:.1f}% of decks")
        syn = rec.get("synergy_score")
        if syn and syn > 0.1:
            parts.append(f"synergy +{syn:.2f}")
    if vscore > 0.5:
        parts.append(f"thematic match {vscore:.2f}")
    prim = get_primary(roles)
    parts.append(f"role: {prim.replace('_', ' ')}")

    return CardScore(
        normalized_name=candidate.normalized_name,
        name=candidate.name,
        roles=roles,
        primary_role=prim,
        edhrec_score=round(edhrec, 4),
        vector_score=round(vscore, 4),
        role_need_score=round(role_need, 4),
        synergy_score=round(synergy, 4),
        curve_score=round(curve, 4),
        final_score=round(min(final, 1.0), 4),
        explanation="; ".join(parts) or "general synergy",
    )
