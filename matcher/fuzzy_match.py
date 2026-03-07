"""Fuzzy name and model number matching."""

import re

from rapidfuzz import fuzz

from .models import Match, Product


def extract_model_number(product: Product) -> str | None:
    """Extract model number from product name or specifications."""
    specs = product.specifications
    # Check specs first — most reliable
    for key in ["Hersteller Modellnummer", "Modellnummer", "Modellbezeichnung",
                "Modellname"]:
        if key in specs and specs[key]:
            val = specs[key].strip()
            if len(val) >= 4 and any(c.isdigit() for c in val):
                return val.upper()

    # Fall back to extracting from product name
    return _extract_model_from_name(product.name)


def _extract_model_from_name(name: str) -> str | None:
    """Try to extract a model number from a product name."""
    # Look for alphanumeric sequences with digits+letters, >= 4 chars
    candidates = re.findall(r'\b([A-Za-z0-9][A-Za-z0-9._/-]{3,})\b', name)
    # Filter out pure words, pure numbers, years, sizes
    skip = {"smart", "full", "google", "android", "qled", "oled", "ultra",
            "zoll", "inch", "2024", "2025", "2026", "direct", "dolby",
            "vision", "premium", "fernseher", "audio", "mini", "hdr10",
            "hdr10+", "bluetooth", "tizen", "webos", "wifi"}
    for c in candidates:
        c_lower = c.lower()
        if c_lower in skip:
            continue
        has_digit = any(ch.isdigit() for ch in c)
        has_letter = any(ch.isalpha() for ch in c)
        if has_digit and has_letter and len(c) >= 4:
            return c.upper()
    return None


def normalize_name(name: str) -> str:
    """Normalize product name for comparison."""
    name = name.lower()
    for word in ["mit", "und", "für", "the", "with", "and", "for", "von",
                 "online", "kaufen", "bestellen", "günstig"]:
        name = name.replace(f" {word} ", " ")
    name = re.sub(r'\(\d+["\u201d]\)', '', name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name


def _extract_dimensions(name: str) -> set[str]:
    """Extract size/dimension values from product name."""
    # Match patterns like 1,50m, 3.0m, 65", 32 Zoll, 24", etc.
    dims = set()
    for m in re.finditer(r'(\d+[.,]?\d*)\s*(?:m|cm|mm|zoll|"|\')', name.lower()):
        dims.add(m.group(0).strip())
    return dims


def _models_conflict(src_model: str | None, tgt_model: str | None) -> bool:
    """Return True if both have model numbers and they differ."""
    if not src_model or not tgt_model:
        return False
    return src_model != tgt_model


def _dimensions_conflict(src_name: str, tgt_name: str) -> bool:
    """Return True if products have different dimensions/sizes."""
    src_dims = _extract_dimensions(src_name)
    tgt_dims = _extract_dimensions(tgt_name)
    if not src_dims or not tgt_dims:
        return False
    return src_dims != tgt_dims


def match_by_model_number(sources: list[Product], targets: list[Product]) -> list[Match]:
    """Match by extracted model numbers."""
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


def _extract_screen_size(text: str) -> int | None:
    """Extract screen size in inches from product text."""
    for m in re.finditer(r'(\d{2,3})\s*(?:"|zoll|inch)', text.lower()):
        val = int(m.group(1))
        if 20 <= val <= 100:
            return val
    for m in re.finditer(r'(\d{2,3})\s*cm', text.lower()):
        cm = int(m.group(1))
        inches = round(cm / 2.54)
        if 20 <= inches <= 100:
            return inches
    return None


def _extract_model_series(model: str) -> str | None:
    """Extract core series identifier from a full TV model number.

    E.g. QE55Q7FAAUXXN -> Q7F, TQ65Q7FAAU -> Q7F
    """
    m = re.match(r'(?:QE|GQ|TQ|UA)\d{2}([A-Z]\d{1,2}[A-Z]?)', model.upper())
    if m:
        return m.group(1)
    return None


def _strip_model_suffix(model: str) -> str:
    """Strip region/variant suffix from model number.

    E.g. 32LQ63006LA.AEU -> 32LQ63006, QE55Q7FAAUXXN -> QE55Q7F
    """
    model = model.split(".")[0]
    model = re.sub(r'[A-Z]{2,}$', '', model)
    return model


def match_by_model_series(
    sources: list[Product],
    targets: list[Product],
    already_matched: set[tuple[str, str]] | None = None,
) -> list[Match]:
    """Match by brand + model series + screen size.

    Catches cases where the target listing doesn't have a clean model number
    but mentions the series name (e.g. 'Q7F') and size in the product name.
    """
    already_matched = already_matched or set()
    matches = []

    for source in sources:
        src_model = extract_model_number(source)
        if not src_model:
            continue
        src_series = _extract_model_series(src_model)
        if not src_series:
            continue
        src_size = _extract_screen_size(source.name)
        if not src_size:
            continue

        for target in targets:
            if (source.reference, target.reference) in already_matched:
                continue
            if source.brand and target.brand:
                if source.brand.lower() != target.brand.lower():
                    continue

            tgt_model = extract_model_number(target)
            tgt_series = _extract_model_series(tgt_model) if tgt_model else None

            series_match = False
            if tgt_series and tgt_series == src_series:
                series_match = True
            elif src_series in target.name.upper():
                series_match = True

            if not series_match:
                continue

            tgt_size = _extract_screen_size(target.name)
            if not tgt_size or src_size != tgt_size:
                continue

            matches.append(Match(
                source_reference=source.reference,
                target_reference=target.reference,
                target_name=target.name,
                target_retailer=target.retailer or "",
                target_url=target.url or "",
                target_price=target.price_eur,
                confidence=0.90,
                method="model_series",
            ))

    return matches


def match_by_fuzzy_model(
    sources: list[Product],
    targets: list[Product],
    already_matched: set[tuple[str, str]] | None = None,
) -> list[Match]:
    """Match by fuzzy model number comparison within same brand + screen size.

    Catches regional variants like 32LQ63806LC vs 32LQ63006LA where model
    numbers share a common prefix but differ in suffix.
    """
    already_matched = already_matched or set()
    matches = []

    for source in sources:
        src_model = extract_model_number(source)
        if not src_model:
            continue
        src_stripped = _strip_model_suffix(src_model)
        if len(src_stripped) < 6:
            continue
        src_size = _extract_screen_size(source.name)

        for target in targets:
            if (source.reference, target.reference) in already_matched:
                continue
            if source.brand and target.brand:
                if source.brand.lower() != target.brand.lower():
                    continue

            tgt_model = extract_model_number(target)
            if not tgt_model:
                continue
            if src_model == tgt_model:
                continue

            tgt_stripped = _strip_model_suffix(tgt_model)
            if len(tgt_stripped) < 6:
                continue

            prefix_len = 0
            for a, b in zip(src_stripped, tgt_stripped):
                if a == b:
                    prefix_len += 1
                else:
                    break
            if prefix_len < 6:
                continue

            tgt_size = _extract_screen_size(target.name)
            if src_size and tgt_size and src_size != tgt_size:
                continue

            matches.append(Match(
                source_reference=source.reference,
                target_reference=target.reference,
                target_name=target.name,
                target_retailer=target.retailer or "",
                target_url=target.url or "",
                target_price=target.price_eur,
                confidence=0.88,
                method="fuzzy_model",
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
        src_model = extract_model_number(source)

        candidates = []
        if source.brand:
            candidates = brand_targets.get(source.brand.lower(), [])
        candidates = candidates + no_brand_targets

        for target in candidates:
            if (source.reference, target.reference) in already_matched:
                continue

            # If both have model numbers and they differ, skip
            tgt_model = extract_model_number(target)
            if _models_conflict(src_model, tgt_model):
                continue

            # If dimensions/sizes differ, skip (e.g. 1.5m vs 3.0m cable)
            if _dimensions_conflict(source.name, target.name):
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


def verify_scraped_match(source: Product, scraped_name: str) -> float:
    """Score how well a scraped product name matches a source product.

    Returns a confidence score 0.0-1.0. Used to filter bad scrape results.
    """
    src_model = extract_model_number(source)
    src_name = normalize_name(source.name)
    scraped_norm = normalize_name(scraped_name)

    # Check if model number appears in scraped name
    if src_model and src_model.upper() in scraped_name.upper():
        return 0.95

    # Check brand presence
    brand_present = source.brand and source.brand.lower() in scraped_name.lower()

    # Check screen size match
    src_size = _extract_screen_size(source.name)
    scraped_size = _extract_screen_size(scraped_name)
    size_match = src_size and scraped_size and src_size == scraped_size

    # Fuzzy name score
    fuzzy_score = fuzz.token_sort_ratio(src_name, scraped_norm) / 100.0

    # Combine signals
    score = fuzzy_score
    if brand_present:
        score = min(score + 0.1, 1.0)
    if size_match:
        score = min(score + 0.05, 1.0)
    if brand_present and size_match and fuzzy_score >= 0.5:
        score = max(score, 0.85)

    return min(score, 1.0)
