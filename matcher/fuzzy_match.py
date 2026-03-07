"""Fuzzy name and model number matching."""

import re

from rapidfuzz import fuzz

from .models import Match, Product


def extract_model_number(product: Product) -> str | None:
    """Extract model number from product name or specifications."""
    # Check specs first — most reliable
    specs = product.specifications
    for key in ["Hersteller Modellnummer", "Modellnummer", "Modellbezeichnung",
                "Model", "model", "Modellname", "Art.-Nr."]:
        if key in specs and specs[key]:
            val = specs[key].strip()
            if len(val) >= 4:
                return val.upper()

    # Fall back to extracting from product name
    return _extract_model_from_name(product.name)


def _extract_model_from_name(name: str) -> str | None:
    """Try to extract a model number from a product name."""
    # Look for alphanumeric sequences with digits+letters, >= 4 chars
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
    for word in ["mit", "und", "für", "the", "with", "and", "for", "von",
                 "online", "kaufen", "bestellen", "günstig"]:
        name = name.replace(f" {word} ", " ")
    # Remove size/dimension patterns like (65") or 65 Zoll
    name = re.sub(r'\(\d+["\u201d]\)', '', name)
    # Collapse whitespace
    name = re.sub(r'\s+', ' ', name).strip()
    return name


def match_by_model_number(sources: list[Product], targets: list[Product]) -> list[Match]:
    """Match by extracted model numbers."""
    # Build index: model_number -> targets (brand-agnostic for wider recall)
    model_index: dict[str, list[Product]] = {}
    for t in targets:
        model = extract_model_number(t)
        if model:
            model_index.setdefault(model, []).append(t)

    matches = []
    for source in sources:
        model = extract_model_number(source)
        if not model:
            continue
        if model in model_index:
            for target in model_index[model]:
                # If both have brands, they should match
                if source.brand and target.brand:
                    if source.brand.lower() != target.brand.lower():
                        continue
                matches.append(Match(
                    source_reference=source.reference,
                    target_reference=target.reference,
                    target_name=target.name,
                    target_retailer=target.retailer or "",
                    target_url=target.url or "",
                    target_price=target.price_eur,
                    confidence=0.95,
                    method="model_number",
                ))

    return matches


def match_by_fuzzy_name(
    sources: list[Product],
    targets: list[Product],
    threshold: float = 82.0,
    already_matched: set[tuple[str, str]] | None = None,
) -> list[Match]:
    """Fuzzy match by normalized product name, optionally within same brand."""
    already_matched = already_matched or set()

    # Group targets by brand for efficiency
    brand_targets: dict[str, list[Product]] = {}
    no_brand_targets: list[Product] = []
    for t in targets:
        if t.brand:
            brand_targets.setdefault(t.brand.lower(), []).append(t)
        else:
            no_brand_targets.append(t)

    matches = []
    for source in sources:
        src_name = normalize_name(source.name)

        # Search same-brand targets first
        candidates = []
        if source.brand:
            candidates = brand_targets.get(source.brand.lower(), [])

        # Also search no-brand targets
        candidates = candidates + no_brand_targets

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
