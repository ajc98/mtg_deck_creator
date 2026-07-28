# Hybrid Scoring Algorithm

## Goal

Build a scoring system that balances:

1. legality,
2. EDHREC recommendation signals,
3. vector similarity,
4. role needs,
5. mana curve,
6. synergy,
7. collection availability,
8. budget,
9. deck balance.

## Card Score Components

Suggested normalized features:

```text
final_score =
    0.25 * edhrec_score
  + 0.20 * vector_similarity_score
  + 0.20 * role_need_score
  + 0.15 * commander_synergy_score
  + 0.10 * mana_curve_score
  + 0.05 * collection_score
  + 0.05 * budget_score
```

These weights should be configurable.

## Important

Weights should change depending on deck-building phase.

Example:

For early candidate discovery:

- EDHREC: high
- Vector: high
- Role: medium

For final deck construction:

- Role need: very high
- Mana curve: high
- Redundancy control: high
- EDHREC/vector: supporting signals

## EDHREC Score

Possible formula:

```text
edhrec_score =
    0.60 * normalized_deck_percentage
  + 0.30 * normalized_synergy_score
  + 0.10 * section_importance_score
```

If only some fields exist, rescale available components.

## Vector Similarity Score

Use cosine similarity normalized between 0 and 1.

Avoid selecting 30 cards that are textually similar but all do the same thing.

## Role Need Score

The deck builder should know current missing roles.

Example:

If current deck has only 3 ramp cards and target is 10, ramp cards get a higher role score.

If current deck already has enough board wipes, another board wipe gets a lower role score.

## Commander Synergy Score

Can be based on:

- known commander themes,
- EDHREC sections,
- card role,
- keyword overlap,
- mechanic overlap,
- manually derived tags from Oracle text,
- LLM-assisted classification if available.

## Mana Curve Score

Prefer cards that support a healthy curve.

Consider:

- commander mana value,
- average mana value,
- number of 1-drops, 2-drops, 3-drops,
- too many expensive cards,
- deck archetype.

## Collection Score

If using an owned collection:

- owned card: 1.0
- not owned but allowed: 0.2
- not owned and `--owned-only`: excluded

## Budget Score

If price data is available:

- cheaper cards get higher score under budget mode,
- expensive cards still allowed if they are essential and budget allows.

## Deck-Level Optimization

Do not simply sort by final_score and take top 99.

Instead:

1. Add commander.
2. Build candidate pool.
3. Fill mandatory categories:
   - lands,
   - ramp,
   - draw,
   - interaction,
   - synergy,
   - win conditions.
4. Validate legality.
5. Check curve.
6. Remove redundant low-impact cards.
7. Rebalance roles.
8. Produce final 100-card deck.
