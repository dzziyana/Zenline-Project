"""Fuzzy name and model number matching."""

import re

from rapidfuzz import fuzz

from .models import Match, Product


def extract_model_number(name: str) -> str | None:
    """Try to extract a model number from a product name.

    Model numbers typically contain digits mixed with letters,
    e.g. 'SMS4HVW33E', 'GV3D850', 'KGN39VICT'.
    """
    # Look for alphanumeric sequences with at least one digit and one letter, >= 4 chars
    candidates = re.findall(r'\b([A-Za-z0-9](?:[A-Za-z0-9._/-]){3,})\b', name)
    for c in candidates:
        has_digit = any(ch.isdigit() for ch in c)
        has_letter = any(ch.isalpha() for ch in c)
        if has_digit and has_letter and len(c) >= 4:
            return c.upper()
    return None


def normalize_name(name: str) -> str:
    """Normalize product name for comparison."""
    name = name.lower()
    # Remove common filler words
    for word in ["mit", "und", "für", "the", "with", "and", "for", "von"]:
        name = name.replace(f" {word} ", " ")
    # Collapse whitespace
    name = re.sub(r'\s+', ' ', name).strip()
    return name


def match_by_model_number(sources: list[Product], targets: list[Product]) -> list[Match]:
    """Match by extracted model numbers within the same brand."""
    # Build index: (brand_lower, model_number) -> targets
    model_index: dict[tuple[str, str], list[Product]] = {}
    for t in targets:
        model = extract_model_number(t.name)
        if model and t.brand:
            key = (t.brand.lower(), model)
            model_index.setdefault(key, []).append(t)

    matches = []
    for source in sources:
        model = extract_model_number(source.name)
        if not model or not source.brand:
            continue
        key = (source.brand.lower(), model)
        if key in model_index:
            for target in model_index[key]:
                matches.append(Match(
                    source_reference=source.reference,
                    target_reference=target.reference,
                    target_name=target.name,
                    target_retailer=target.retailer or "",
                    target_url=target.url or "",
                    target_price=target.price_eur,
                    confidence=0.9,
                    method="model_number",
                ))

    return matches


def match_by_fuzzy_name(
    sources: list[Product],
    targets: list[Product],
    threshold: float = 85.0,
    already_matched: set[tuple[str, str]] | None = None,
) -> list[Match]:
    """Fuzzy match by normalized product name within the same brand."""
    already_matched = already_matched or set()

    # Group targets by brand
    brand_targets: dict[str, list[Product]] = {}
    for t in targets:
        if t.brand:
            brand_targets.setdefault(t.brand.lower(), []).append(t)

    matches = []
    for source in sources:
        if not source.brand:
            continue
        brand_key = source.brand.lower()
        candidates = brand_targets.get(brand_key, [])
        if not candidates:
            continue

        src_name = normalize_name(source.name)
        for target in candidates:
            if (source.reference, target.reference) in already_matched:
                continue
            tgt_name = normalize_name(target.name)
            score = fuzz.token_sort_ratio(src_name, tgt_name)
            if score >= threshold:
                matches.append(Match(
                    source_reference=source.reference,
                    target_reference=target.reference,
                    target_name=target.name,
                    target_retailer=target.retailer or "",
                    target_url=target.url or "",
                    target_price=target.price_eur,
                    confidence=score / 100.0,
                    method="fuzzy_name",
                ))

    return matches
