# CLI Requirements

## CLI Philosophy

The CLI should be the first complete interface.

It should be easy to inspect, debug, and iterate.

## Commands

### Ingest Scryfall

```bash
python -m mtgdeck ingest scryfall --file oracle-cards.json
```

Responsibilities:

- load Scryfall Oracle JSON,
- normalize card data,
- insert/update DuckDB cards table,
- detect basic lands,
- detect Commander legality,
- build searchable text.

### Ingest Collection

```bash
python -m mtgdeck ingest collection --file moxfield.csv
```

Responsibilities:

- import owned cards,
- normalize card names,
- store quantities,
- support future owned-only deck generation.

### Cache EDHREC

```bash
python -m mtgdeck cache-edhrec "Commander Name"
```

Responsibilities:

- fetch commander page,
- parse recommendations,
- store raw and parsed data,
- avoid repeated fetching.

### Embed Cards

```bash
python -m mtgdeck embed cards --model local
```

Responsibilities:

- create embeddings for cards,
- store embeddings,
- skip already embedded cards unless `--force`.

### Build Deck

```bash
python -m mtgdeck build "Commander Name" --owned-only
```

Options:

```bash
--owned-only
--allow-unowned
--budget 300
--theme aristocrats
--power casual
--power optimized
--power high-power
--lands 36
--explain
--output decklist.txt
```

### Validate Deck

```bash
python -m mtgdeck validate decklist.txt --commander "Commander Name"
```

Responsibilities:

- check deck size,
- singleton rule,
- color identity,
- Commander legality,
- banned cards,
- basic land exceptions.

### Explain Deck

```bash
python -m mtgdeck explain --deck-id <id>
```

Responsibilities:

- show card-by-card reasons,
- show role counts,
- show mana curve,
- show weak points.

## CLI Output

Use `rich` tables.

Output sections:

1. Commander Profile
2. Deck Summary
3. Role Counts
4. Mana Curve
5. Legality Check
6. Final Decklist
7. Card Explanations
8. Warnings and Improvement Suggestions
