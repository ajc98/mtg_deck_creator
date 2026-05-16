"""Rich terminal output helpers for deck results."""
from __future__ import annotations

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box


def print_deck_summary(
    console: Console,
    commander_name: str,
    cards: list[dict],
    role_counts: dict[str, int],
    warnings: list[str],
) -> None:
    total = 1 + len(cards)  # commander + 99
    land_count = sum(1 for c in cards if c.get("is_land"))

    summary = Table(title=f"Deck: {commander_name}", box=box.ROUNDED, show_header=False)
    summary.add_column("", style="bold")
    summary.add_column("")
    summary.add_row("Total cards", str(total))
    summary.add_row("Lands", str(land_count))
    summary.add_row("Non-lands", str(len(cards) - land_count))
    console.print(summary)

    if warnings:
        for w in warnings:
            console.print(f"[yellow]⚠[/yellow]  {w}")


def print_role_breakdown(
    console: Console,
    role_counts: dict[str, int],
) -> None:
    table = Table(title="Role Breakdown", box=box.SIMPLE)
    table.add_column("Role", style="bold")
    table.add_column("Count", justify="right")
    for role, count in sorted(role_counts.items()):
        table.add_row(role.replace("_", " ").title(), str(count))
    console.print(table)


def print_mana_curve(console: Console, cards: list[dict]) -> None:
    from mtgdeck.scoring.mana_curve import curve_health

    cmcs = [c.get("cmc") or 0.0 for c in cards if not c.get("is_land")]
    health = curve_health(cmcs)

    table = Table(title="Mana Curve (non-lands)", box=box.SIMPLE)
    table.add_column("CMC", justify="right", style="bold")
    table.add_column("Count", justify="right")
    for bucket, count in sorted(health["counts"].items(), key=lambda x: x[0]):
        label = f"{bucket}+" if bucket == 7 else str(bucket)
        table.add_row(label, str(count))
    table.add_row("[dim]avg[/dim]", f"[dim]{health['average']:.2f}[/dim]")
    console.print(table)

    for w in health.get("warnings", []):
        console.print(f"[yellow]⚠[/yellow]  {w}")


def print_validation(console: Console, result) -> None:
    from mtgdeck.rules.deck_validator import ValidationResult

    if result.valid:
        console.print("[green]✓ Deck is valid.[/green]")
    else:
        console.print("[red]✗ Deck validation FAILED.[/red]")
    for err in result.errors:
        console.print(f"  [red]• {err}[/red]")
    for warn in result.warnings:
        console.print(f"  [yellow]• {warn}[/yellow]")


def print_top_cards(
    console: Console,
    card_scores,   # list[CardScore]
    limit: int = 20,
) -> None:
    table = Table(title=f"Top {limit} Cards by Score", box=box.SIMPLE)
    table.add_column("#", justify="right", style="dim")
    table.add_column("Card", style="bold")
    table.add_column("Role")
    table.add_column("Score", justify="right")
    table.add_column("EDHREC", justify="right")
    table.add_column("Vector", justify="right")

    for i, s in enumerate(sorted(card_scores, key=lambda x: x.final_score, reverse=True)[:limit], 1):
        table.add_row(
            str(i),
            s.name,
            s.primary_role,
            f"{s.final_score:.3f}",
            f"{s.edhrec_score:.3f}",
            f"{s.vector_score:.3f}",
        )
    console.print(table)
