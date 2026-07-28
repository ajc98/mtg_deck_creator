# Commander Rules Claude Must Respect

## Deck Size

A Commander deck has exactly 100 cards total, including the commander.

For normal Commander:

- 1 commander card.
- 99 main deck cards.

For partner/background/special cases, support can be added later.  
Initial version should focus on one commander unless the architecture makes partner support easy.

## Singleton Rule

Except for basic lands and cards that explicitly override deck construction rules, a Commander deck can only contain one copy of each card by English card name.

Basic lands may have multiple copies:

- Plains
- Island
- Swamp
- Mountain
- Forest
- Wastes

Some cards may override the singleton rule, for example:

- Persistent Petitioners
- Relentless Rats
- Rat Colony
- Shadowborn Apostle
- Dragon's Approach
- Hare Apparent

These special cases should be data-driven when possible, by checking Oracle text for wording like:

> A deck can have any number of cards named...

## Color Identity

Every card in the deck must be within the commander's color identity.

A card's color identity includes:

- mana symbols in mana cost,
- mana symbols in Oracle text,
- color indicator,
- characteristic-defining color identity rules.

Use Scryfall's `color_identity` field as the source of truth when available.

A card is legal if:

```python
set(card.color_identity).issubset(set(commander.color_identity))
```

Colorless cards are legal in any Commander deck.

## Commander Card

The chosen commander must be a legal commander.

Initially detect legal commanders by checking Scryfall fields:

- `legalities.commander == "legal"`
- and/or type line contains `Legendary Creature`
- later support special cases:
  - planeswalkers that can be commanders,
  - Background,
  - Partner,
  - Doctor's companion,
  - Choose a Background,
  - Friends forever.

## Banned Cards

Respect Commander legality from Scryfall.

Exclude cards where:

```python
legalities.commander != "legal"
```

Do not include banned cards even if they score highly.

## Land Rules

Lands also follow color identity.

Example:

- `Command Tower` is colorless identity and legal anywhere.
- `Bojuka Bog` has black color identity? Use Scryfall as source of truth.
- Fetch lands and utility lands must be validated using Scryfall color identity.

The deck should normally include around 34–38 lands unless commander strategy indicates otherwise.

## Validation Output

Every generated deck must be validated after construction.

Validation should check:

- exactly 100 cards including commander,
- no illegal color identity cards,
- no Commander-banned cards,
- no singleton violations,
- legal commander,
- reasonable land count,
- basic land exception,
- role balance warnings.
