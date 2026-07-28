# Vector Search Instructions

## Purpose

Vector search should find cards that are semantically related to:

- commander Oracle text,
- commander strategy,
- deck archetype,
- desired role,
- custom user prompt.

But vector search is not enough by itself.

## Card Search Text

Create a searchable text field per card:

```text
Name: {name}
Type: {type_line}
Mana Cost: {mana_cost}
Mana Value: {cmc}
Colors: {colors}
Color Identity: {color_identity}
Oracle Text: {oracle_text}
Keywords: {keywords}
Power/Toughness: {power}/{toughness}
Legalities: commander={commander_legality}
```

Optionally include derived tags:

```text
Roles: ramp, removal, card draw, sacrifice outlet, token producer
Themes: aristocrats, lifegain, graveyard, artifacts
```

## Embedding Granularity

Start with one embedding per card.

Later, consider multiple embeddings per card:

- full card,
- Oracle text only,
- role-focused summary,
- combo/synergy summary.

## Vector Search Query Examples

For a commander:

```text
Find cards that support this commander strategy:
Commander: K'rrik, Son of Yawgmoth
Text: ...
Themes: lifepay, black devotion, storm, sacrifice, graveyard recursion
Needed roles: ramp, card draw, protection, win conditions
```

For specific roles:

```text
Find mono-black ramp cards for a K'rrik Commander deck.
```

```text
Find sacrifice outlets and aristocrat payoffs for a black Commander deck.
```

## Filtering Before Scoring

Always filter candidates before scoring:

- Commander legal.
- Color identity subset of commander.
- Not banned in Commander.
- Not already included unless basic land or special rule.
- Available in collection if `--owned-only` is used.

## Similarity Score

Store cosine similarity as `vector_similarity_score`.

Normalize to 0–1.

Do not let vector similarity dominate everything.

A perfect text match can still be a bad deck-building choice if the deck lacks ramp, draw, or lands.
