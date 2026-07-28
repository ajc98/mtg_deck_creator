# MTG Commander Domain Knowledge for Claude

## Do Not Over-Rely on Text Similarity

Cards with similar Oracle text to the commander are not always the best cards.

Example:

A sacrifice commander may need:

- token makers,
- sacrifice outlets,
- death triggers,
- recursion,
- card draw,
- aristocrat payoffs,
- tutors,
- protection,
- mana acceleration.

Some of these cards may not mention the commander's exact mechanics.

## Core Deck Roles

Every generated deck should attempt to classify cards into roles.

Suggested roles:

- Commander
- Ramp
- Mana rock
- Mana dork
- Land ramp
- Card draw
- Card selection
- Tutor
- Single-target removal
- Board wipe
- Protection
- Recursion
- Graveyard hate
- Synergy enabler
- Synergy payoff
- Combo piece
- Win condition
- Token producer
- Sacrifice outlet
- Lifegain
- Lifepay enabler
- Counterspell
- Stax
- Land
- Utility land
- Basic land

## Suggested Commander Deck Baselines

These are not hard rules, but useful heuristics:

- Lands: 34–38
- Ramp: 8–12
- Card draw/card advantage: 8–12
- Single-target interaction: 6–10
- Board wipes: 2–4
- Protection: 2–6
- Main synergy pieces: 20–35
- Win conditions/payoffs: 4–8

Deck archetype may change these values.

## Commander Profile

For each commander, build a profile:

- name,
- color identity,
- mana value,
- type line,
- Oracle text,
- keywords,
- likely archetypes,
- mechanical themes,
- required support roles,
- known EDHREC themes if available.

## Example

For `K'rrik, Son of Yawgmoth`, important themes may include:

- black devotion,
- lifepay,
- fast mana,
- storm-like lines,
- sacrifice,
- aristocrats,
- tutors,
- graveyard recursion,
- Bolas's Citadel-style topdeck engines,
- lifegain to offset life payment.

Do not only search for cards that mention "life" or "Phyrexian mana".  
The deck also needs black staples, mana engines, draw, removal, protection, and win conditions.
