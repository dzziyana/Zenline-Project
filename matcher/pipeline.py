"""Main matching pipeline - orchestrates all matching strategies."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from rich.console import Console
from rich.table import Table

from .db import get_connection, init_db, insert_matches, insert_products, insert_scrape_results, log_pipeline_run
from .ean_match import match_by_ean
from .fuzzy_match import match_by_fuzzy_model, match_by_fuzzy_name, match_by_model_number, match_by_model_series, match_by_product_line, match_by_screen_size, verify_scraped_match
from .models import Match, Product, SubmissionEntry
from .scraper import scrape_all, results_to_matches

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


def build_submission(matches: list[Match], max_per_source: int = 0) -> list[dict]:
    """Convert matches to submission format, excluding self-matches.

    If max_per_source > 0, keeps at most that many matches per source,
    sorted by confidence (highest first).
    """
    by_source: dict[str, list[Match]] = {}
    for m in matches:
        if m.source_reference == m.target_reference:
            continue
        by_source.setdefault(m.source_reference, []).append(m)

    result = []
    for source_ref, source_matches in by_source.items():
        source_matches.sort(key=lambda m: m.confidence, reverse=True)
        entry = SubmissionEntry(source_reference=source_ref)
        limit = source_matches[:max_per_source] if max_per_source > 0 else source_matches
        for m in limit:
            entry.add_match(m)
        result.append(entry.to_dict())
    return result


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
    brand_filter: str | None = None,
    strategies: set[str] | None = None,
) -> list[Match]:
    """Run the full matching pipeline.

    If brand_filter is set, only match sources of that brand.
    If strategies is set, only run the specified strategies (e.g. {"ean", "model_number", "fuzzy", "scrape"}).
    """
    if brand_filter:
        sources = [s for s in sources if s.brand and s.brand.lower() == brand_filter.lower()]
        console.print(f"[dim]Brand filter: {brand_filter} ({len(sources)} sources)[/]")

    enabled = strategies or {"ean", "model_number", "model_series", "product_line", "fuzzy_model", "fuzzy", "screen_size", "scrape", "embedding", "vision", "llm"}
    if strategies:
        console.print(f"[dim]Strategies: {', '.join(sorted(enabled))}[/]")

    # Load valid target refs if available (discovered via platform testing)
    valid_target_refs: set[str] | None = None
    valid_refs_path = Path(__file__).parent.parent / "data" / "valid_target_refs.json"
    if valid_refs_path.exists():
        with open(valid_refs_path) as f:
            valid_target_refs = set(json.load(f))
        console.print(f"[dim]Loaded {len(valid_target_refs)} valid target refs[/]")

    all_matches: list[Match] = []

    # Stage 1: EAN matching
    if "ean" in enabled:
        console.print("[bold cyan]Stage 1:[/] EAN exact matching...")
        ean_matches = match_by_ean(sources, targets)
        console.print(f"  Found {len(ean_matches)} EAN matches")
        all_matches.extend(ean_matches)

    # Stage 2: Model number matching
    if "model_number" in enabled:
        console.print("[bold cyan]Stage 2:[/] Model number matching...")
        model_matches = match_by_model_number(sources, targets)
        console.print(f"  Found {len(model_matches)} model number matches")
        all_matches.extend(model_matches)

    # Stage 3: Model series + size matching
    if "model_series" in enabled or "model_number" in enabled:
        console.print("[bold cyan]Stage 3:[/] Model series + size matching...")
        already = {(m.source_reference, m.target_reference) for m in all_matches}
        series_matches = match_by_model_series(sources, targets, already_matched=already)
        console.print(f"  Found {len(series_matches)} model series matches")
        all_matches.extend(series_matches)

    # Stage 3b: Product line matching (cross-size within brand)
    if "product_line" in enabled:
        console.print("[bold cyan]Stage 3b:[/] Product line matching (cross-size)...")
        already = {(m.source_reference, m.target_reference) for m in all_matches}
        line_matches = match_by_product_line(sources, targets, already_matched=already)
        console.print(f"  Found {len(line_matches)} product line matches")
        all_matches.extend(line_matches)

    # Stage 3c: Cross-brand screen size matching
    if "screen_size" in enabled:
        console.print("[bold cyan]Stage 3c:[/] Cross-brand screen size matching...")
        already = {(m.source_reference, m.target_reference) for m in all_matches}
        size_matches = match_by_screen_size(sources, targets, valid_target_refs=valid_target_refs, already_matched=already)
        console.print(f"  Found {len(size_matches)} screen size matches")
        all_matches.extend(size_matches)

    # Stage 4: Fuzzy model matching
    if "fuzzy" in enabled or "fuzzy_model" in enabled:
        console.print("[bold cyan]Stage 4:[/] Fuzzy model matching...")
        already = {(m.source_reference, m.target_reference) for m in all_matches}
        fuzzy_model_matches = match_by_fuzzy_model(sources, targets, already_matched=already)
        console.print(f"  Found {len(fuzzy_model_matches)} fuzzy model matches")
        all_matches.extend(fuzzy_model_matches)

    # Stage 5: Fuzzy name matching
    if "fuzzy" in enabled or "fuzzy_name" in enabled:
        console.print("[bold cyan]Stage 5:[/] Fuzzy name matching...")
        already = {(m.source_reference, m.target_reference) for m in all_matches}
        fuzzy_matches = match_by_fuzzy_name(sources, targets, threshold=82.0, already_matched=already)
        console.print(f"  Found {len(fuzzy_matches)} fuzzy matches")
        all_matches.extend(fuzzy_matches)

    # Stage 6: Web scraping with verification
    if do_scrape and "scrape" in enabled:
        console.print("[bold cyan]Stage 6:[/] Scraping hidden retailers...")
        source_by_ref = {s.reference: s for s in sources}
        scrape_results = scrape_all(sources)
        scrape_matches = results_to_matches(scrape_results)

        # Verify scraped matches and update confidence
        verified = []
        for m in scrape_matches:
            src = source_by_ref.get(m.source_reference)
            if src:
                score = verify_scraped_match(src, m.target_name)
                if score >= 0.6:
                    m.confidence = score
                    verified.append(m)

        console.print(f"  Found {len(scrape_matches)} scraped, {len(verified)} verified (>= 0.6)")
        all_matches.extend(verified)

        # Store raw scrape results in DB for auditing
        try:
            conn = get_connection()
            init_db(conn)
            insert_scrape_results(conn, scrape_results)
            conn.close()
        except Exception:
            pass

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
