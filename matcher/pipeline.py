"""Main matching pipeline - orchestrates all matching strategies."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from rich.console import Console
from rich.table import Table

from .db import get_connection, init_db, insert_matches, insert_products, log_pipeline_run
from .ean_match import match_by_ean
from .fuzzy_match import match_by_fuzzy_model, match_by_fuzzy_name, match_by_model_number, match_by_model_series
from .models import Match, Product, SubmissionEntry
from .scraper import scrape_all

console = Console()


def load_products(path: Path) -> list[Product]:
    """Load products from a JSON file."""
    with open(path) as f:
        data = json.load(f)
    return [Product.from_dict(d) for d in data]


def dedupe_matches(matches: list[Match]) -> list[Match]:
    """Remove duplicate (source, target) pairs, keeping highest confidence."""
    best: dict[tuple[str, str], Match] = {}
    for m in matches:
        key = (m.source_reference, m.target_reference)
        if key not in best or m.confidence > best[key].confidence:
            best[key] = m
    return list(best.values())


def build_submission(matches: list[Match]) -> list[dict]:
    """Convert matches to submission format."""
    by_source: dict[str, SubmissionEntry] = {}
    for m in matches:
        if m.source_reference not in by_source:
            by_source[m.source_reference] = SubmissionEntry(source_reference=m.source_reference)
        by_source[m.source_reference].add_match(m)
    return [entry.to_dict() for entry in by_source.values()]


def print_summary(matches: list[Match], sources: list[Product]):
    """Print a summary of matching results."""
    table = Table(title="Matching Summary")
    table.add_column("Method", style="cyan")
    table.add_column("Matches", justify="right", style="green")

    by_method: dict[str, int] = {}
    for m in matches:
        by_method[m.method] = by_method.get(m.method, 0) + 1

    for method, count in sorted(by_method.items()):
        table.add_row(method, str(count))

    table.add_section()
    matched_sources = {m.source_reference for m in matches}
    table.add_row("Total matches", str(len(matches)), style="bold")
    table.add_row("Sources matched", f"{len(matched_sources)}/{len(sources)}", style="bold")

    console.print(table)


def run_matching(
    sources: list[Product],
    targets: list[Product],
    do_scrape: bool = True,
) -> list[Match]:
    """Run the full matching pipeline."""
    all_matches: list[Match] = []

    # Stage 1: EAN matching
    console.print("[bold cyan]Stage 1:[/] EAN exact matching...")
    ean_matches = match_by_ean(sources, targets)
    console.print(f"  Found {len(ean_matches)} EAN matches")
    all_matches.extend(ean_matches)

    # Stage 2: Model number matching
    console.print("[bold cyan]Stage 2:[/] Model number matching...")
    model_matches = match_by_model_number(sources, targets)
    console.print(f"  Found {len(model_matches)} model number matches")
    all_matches.extend(model_matches)

    # Stage 3: Model series + size matching
    console.print("[bold cyan]Stage 3:[/] Model series + size matching...")
    already = {(m.source_reference, m.target_reference) for m in all_matches}
    series_matches = match_by_model_series(sources, targets, already_matched=already)
    console.print(f"  Found {len(series_matches)} model series matches")
    all_matches.extend(series_matches)

    # Stage 4: Fuzzy model matching
    console.print("[bold cyan]Stage 4:[/] Fuzzy model matching...")
    already = {(m.source_reference, m.target_reference) for m in all_matches}
    fuzzy_model_matches = match_by_fuzzy_model(sources, targets, already_matched=already)
    console.print(f"  Found {len(fuzzy_model_matches)} fuzzy model matches")
    all_matches.extend(fuzzy_model_matches)

    # Stage 5: Fuzzy name matching
    console.print("[bold cyan]Stage 5:[/] Fuzzy name matching...")
    already = {(m.source_reference, m.target_reference) for m in all_matches}
    fuzzy_matches = match_by_fuzzy_name(sources, targets, threshold=82.0, already_matched=already)
    console.print(f"  Found {len(fuzzy_matches)} fuzzy matches")
    all_matches.extend(fuzzy_matches)

    # Stage 6: Web scraping
    if do_scrape:
        console.print("[bold cyan]Stage 6:[/] Scraping hidden retailers...")
        scrape_matches = asyncio.run(scrape_all(sources))
        console.print(f"  Found {len(scrape_matches)} scraped matches")
        all_matches.extend(scrape_matches)

    # Deduplicate
    all_matches = dedupe_matches(all_matches)

    return all_matches


def run_pipeline(
    source_path: Path,
    target_path: Path,
    output_path: Path,
    category: str = "",
    do_scrape: bool = True,
):
    """Run the full pipeline from files to submission JSON."""
    console.print(f"\n[bold]Product Matcher Pipeline[/]")
    console.print(f"  Sources: {source_path}")
    console.print(f"  Targets: {target_path}")
    if category:
        console.print(f"  Category: {category}")
    console.print()

    sources = load_products(source_path)
    targets = load_products(target_path)
    console.print(f"Loaded {len(sources)} source products, {len(targets)} target products\n")

    matches = run_matching(sources, targets, do_scrape=do_scrape)
    print_summary(matches, sources)

    # Persist to database
    console.print("\n[dim]Saving to database...[/]")
    conn = get_connection()
    init_db(conn)
    insert_products(conn, targets, is_source=False)
    insert_products(conn, sources, is_source=True)
    insert_matches(conn, matches)
    log_pipeline_run(conn, category or "unknown", len(sources), len(targets), matches)
    conn.close()
    console.print("[dim]Database updated.[/]")

    submission = build_submission(matches)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(submission, f, indent=2)
    console.print(f"\n[bold green]Submission saved to {output_path}[/]")
    console.print(f"  {len(submission)} source products with matches")
    total_links = sum(len(e["competitors"]) for e in submission)
    console.print(f"  {total_links} total competitor links")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run product matching pipeline")
    parser.add_argument("--sources", type=Path, required=True, help="Path to source products JSON")
    parser.add_argument("--targets", type=Path, required=True, help="Path to target pool JSON")
    parser.add_argument("--output", type=Path, default=Path("output/submission.json"))
    parser.add_argument("--category", type=str, default="")
    parser.add_argument("--no-scrape", action="store_true", help="Skip web scraping")
    args = parser.parse_args()

    run_pipeline(args.sources, args.targets, args.output, args.category, do_scrape=not args.no_scrape)
