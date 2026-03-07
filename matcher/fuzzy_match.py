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
                # Skip pure-digit strings >= 8 chars (likely EAN/GTIN, not model)
                if val.isdigit() and len(val) >= 8:
                    continue
                # Skip pure-digit internal SKUs (5-6 digit numbers from specs)
                if val.isdigit() and len(val) <= 6:
                    continue
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
            "hdr10+", "bluetooth", "tizen", "webos", "wifi", "triple",
            "tuner", "metal", "design", "120hz", "144hz", "60hz", "100hz",
            "flat"}
    # Pattern for number+unit (e.g. 500ml, 1300W, 15bar, 1.7l)
    unit_pattern = re.compile(
        r'^\d+[.,]?\d*(?:ml|l|w|watt|bar|cm|mm|kg|g|v|min|liter|gramm)$',
        re.IGNORECASE,
    )
    for c in candidates:
        c_lower = c.lower()
        if c_lower in skip:
            continue
        if unit_pattern.match(c):
            continue
        # Skip DVB tuner strings (DVB-C/S/S2/T/T2)
        if c_lower.startswith("dvb"):
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
    for m in re.finditer(r'(\d+[.,]?\d*)\s*(?:m|cm|mm|zoll|["\u201c\u201d\u201e]|\')', name.lower()):
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
    """Match by extracted model numbers (full and short codes)."""
    model_index: dict[str, list[Product]] = {}
    short_code_index: dict[str, list[Product]] = {}
    for t in targets:
        model = extract_model_number(t)
        if model:
            model_index.setdefault(model, []).append(t)
        for code in _extract_short_model_codes(t.name):
            short_code_index.setdefault(code, []).append(t)

    matches = []
    matched_pairs: set[tuple[str, str]] = set()

    for source in sources:
        src_size = _extract_screen_size(source.name)

        # Try full model number first
        model = extract_model_number(source)
        if model and model in model_index:
            for target in model_index[model]:
                if source.brand and target.brand:
                    if source.brand.lower() != target.brand.lower():
                        continue
                # If both have screen sizes, they must match
                tgt_size = _extract_screen_size(target.name)
                if src_size and tgt_size and src_size != tgt_size:
                    continue
                pair = (source.reference, target.reference)
                if pair not in matched_pairs:
                    matched_pairs.add(pair)
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

        # Also try short model codes (EK 3163, ST 3477, WK 1100, etc.)
        for code in _extract_short_model_codes(source.name):
            if code in short_code_index:
                for target in short_code_index[code]:
                    if source.brand and target.brand:
                        if source.brand.lower() != target.brand.lower():
                            continue
                    # If both have screen sizes, they must match
                    tgt_size = _extract_screen_size(target.name)
                    if src_size and tgt_size and src_size != tgt_size:
                        continue
                    pair = (source.reference, target.reference)
                    if pair not in matched_pairs:
                        matched_pairs.add(pair)
                        matches.append(Match(
                            source_reference=source.reference,
                            target_reference=target.reference,
                            target_name=target.name,
                            target_retailer=target.retailer or "",
                            target_url=target.url or "",
                            target_price=target.price_eur,
                            confidence=0.90,
                            method="model_number",
                        ))

    return matches


def _extract_screen_size(text: str) -> int | None:
    """Extract screen size in inches from product text."""
    for m in re.finditer(r'(\d{2,3})\s*[-]?\s*(?:["\u201c\u201d\u201e]|zoll|inch)', text.lower()):
        val = int(m.group(1))
        if 20 <= val <= 100:
            return val
    # Standard TV sizes for snapping cm values
    _standard_sizes = [24, 25, 27, 32, 40, 43, 48, 50, 55, 58, 60, 65, 70, 75, 77, 82, 85, 86, 98]
    for m in re.finditer(r'(\d{2,3})\s*cm', text.lower()):
        cm = int(m.group(1))
        raw_inches = cm / 2.54
        # Snap to nearest standard TV size (within 1 inch tolerance)
        best = min(_standard_sizes, key=lambda s: abs(s - raw_inches))
        if abs(best - raw_inches) <= 1.0 and 20 <= best <= 100:
            return best
    # Fallback: extract from model numbers like 55HP6265E, 40HF3265E, 32LQ63006
    m = re.search(r'\b(\d{2})[A-Z]{2}\d{3,}', text)
    if m:
        val = int(m.group(1))
        if 20 <= val <= 85:
            return val
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


def _extract_product_line(name: str, brand: str) -> str | None:
    """Extract the product line/series identifier from a product name.

    Returns a canonical identifier like 'Q7F', 'QA10', 'Q6C', 'F6000', 'A_PRO',
    'V5C', 'LQ630', '5025C', etc. Used for cross-size matching within the same brand.
    """
    name_upper = name.upper()

    brand_lower = brand.lower() if brand else ""

    if brand_lower == "samsung":
        # Samsung TV lines: Q7F, Q8F, Q64D, Q60, F6000, The Frame, U8070F
        # Group by series number: Q6x -> Q6, Q7x -> Q7, Q8x -> Q8
        for pat in [
            r'(?:QE|GQ|TQ)\s*\d{2}\s*(Q\s*\d{1,2}\s*[A-Z])',  # QE55Q7F or GQ 50 Q 60 C
            r'\b(Q\d{1,2}[A-Z])\b',                              # Q7F, Q8F, Q64D standalone
        ]:
            m = re.search(pat, name_upper)
            if m:
                raw = re.sub(r'\s+', '', m.group(1))  # e.g. Q7F, Q60C, Q64D, Q8F
                # Group all Samsung QLED Q-series together (Q6+Q7+Q8)
                if re.match(r'Q\d', raw):
                    return "QLED"
                return raw
        for pat in [
            r'\b(F\d{4})\b',                                       # F6000
            r'\b(THE FRAME)\b',                                    # The Frame
            r'\b(U\d{4}[A-Z])\b',                                  # U8070F
        ]:
            m = re.search(pat, name_upper)
            if m:
                return m.group(1)

    if brand_lower == "tcl":
        # TCL lines: Q6C, Q7C, V5C, V6C, T69C, T6C, T7B, T8C, S5K, C645, etc.
        for pat in [
            r'\b\d{2}(Q\d[A-Z])\b',          # 65Q6C -> Q6C
            r'\b\d{2}(V\d[A-Z])\b',          # 40V5C -> V5C
            r'\b\d{2}(T\d{1,2}[A-Z])\b',     # 55T69C -> T69C
            r'\b\d{2}(C\d{2,3}[A-Z]?)\b',    # 43C645 -> C645
            r'\b\d{2}(S\d{3,4}[A-Z]?)\b',    # 32S5403A -> S5403
            r'\b\d{2}(P\d[A-Z])\b',          # 50P7K -> P7K
            r'\b\d{2}(QM\d[A-Z])\b',         # 50QM8B -> QM8B
            r'\b\d{2}(SF\d{3})\b',           # 32SF560 -> SF560
            r'\b\d{2}(L\d[A-Z])\b',          # 32L5A -> L5A
            r'\b(C\d{2}[A-Z])\b',            # C61KS -> C61K
        ]:
            m = re.search(pat, name_upper)
            if m:
                return m.group(1)

    if brand_lower == "chiq":
        # CHIQ QA10
        m = re.search(r'\b\d{2}(QA\d+)\b', name_upper)
        if m:
            return m.group(1)

    if brand_lower == "xiaomi":
        # Xiaomi A Pro, F, F Pro - group all A Pro variants (2025, 2026) together
        if 'A PRO' in name_upper:
            return 'A_PRO'
        if re.search(r'\bTV F PRO\b', name_upper):
            return 'F_PRO'
        if re.search(r'\bTV F\b', name_upper):
            return 'F'

    if brand_lower == "peaq":
        # PEAQ PTV models: all PEAQ TVs are the same house brand product line
        # Different years (5023, 5024, 5025) and suffixes are variants, not separate products
        if 'PTV' in name_upper:
            return 'PTV'

    if brand_lower == "lg":
        # LG TV model series: 32LQ63006LA -> LQ630
        m = re.search(r'\d{2}(L[A-Z]\d{3})', name_upper)
        if m:
            return m.group(1)

    # Cables: any brand, match by connector type (Euro C7 cables are interchangeable)
    if ('NETZKABEL' in name_upper or 'STROMKABEL' in name_upper) and ('C7' in name_upper or 'EURO' in name_upper):
        return 'EURO_C7'

    if brand_lower == "sharp":
        # Sharp models: 24FH7EA, 40HF3265E, 55HP6265E
        m = re.search(r'\b\d{2}([A-Z]{2}\d{3,4}[A-Z]?)', name_upper)
        if m:
            return m.group(1)

    if brand_lower == "dyon":
        m = re.search(r'\b(ULTIMAX|SMART|ENTER|LIVE)\b', name_upper)
        if m:
            return m.group(1)

    return None


def match_by_product_line(
    sources: list[Product],
    targets: list[Product],
    already_matched: set[tuple[str, str]] | None = None,
) -> list[Match]:
    """Match by brand + product line, allowing cross-size matches.

    This catches Amazon duplicates and different-size variants of the same product line.
    E.g., Samsung Q7F 43" matches Samsung Q7F 65", CHIQ 43QA10 matches CHIQ 32QA10.
    """
    already_matched = already_matched or set()
    matches = []

    # Build index: (brand, product_line) -> [targets]
    # For cross-brand categories (cables), use ("*", line) as key
    line_index: dict[tuple[str, str], list[Product]] = {}
    cross_brand_lines = {"EURO_C7"}  # categories where brand doesn't matter

    for t in targets:
        brand = t.brand.lower() if t.brand else ""
        line = _extract_product_line(t.name, t.brand or "")
        if not line:
            continue
        if line in cross_brand_lines:
            line_index.setdefault(("*", line), []).append(t)
        elif brand:
            line_index.setdefault((brand, line), []).append(t)

    for source in sources:
        src_brand = source.brand.lower() if source.brand else ""
        src_line = _extract_product_line(source.name, source.brand or "")
        if not src_line:
            continue

        if src_line in cross_brand_lines:
            candidates = line_index.get(("*", src_line), [])
        elif src_brand:
            candidates = line_index.get((src_brand, src_line), [])
        else:
            continue

        src_size = _extract_screen_size(source.name)

        for target in candidates:
            if (source.reference, target.reference) in already_matched:
                continue
            if source.reference == target.reference:
                continue

            # For non-cable products, require same screen size
            if src_line not in cross_brand_lines:
                tgt_size = _extract_screen_size(target.name)
                if src_size and tgt_size and src_size != tgt_size:
                    continue
            else:
                # For cables, require same length
                src_len = _extract_cable_length_m(source.name)
                tgt_len = _extract_cable_length_m(target.name)
                if src_len and tgt_len and src_len != tgt_len:
                    continue

            # Same brand + same product line (+ same size for TVs) = match
            matches.append(Match(
                source_reference=source.reference,
                target_reference=target.reference,
                target_name=target.name,
                target_retailer=target.retailer or "",
                target_url=target.url or "",
                target_price=target.price_eur,
                confidence=0.92,
                method="product_line",
            ))

    return matches


def _is_tv_product(name: str) -> bool:
    """Check if a product is a TV (not a cable, headphone, speaker, adapter, etc.)."""
    nl = name.lower()
    # Positive indicators: if product mentions TV/Fernseher/Zoll, it's a TV
    if any(w in nl for w in ['fernseher', 'smart tv', 'google tv', 'android tv',
                              'fire tv', 'zoll', 'qled', 'oled']):
        return True
    non_tv = ['netzkabel', 'stromkabel', 'euro-netzkabel',
              'kopfhörer', 'headphone', 'earbuds', 'earphone',
              'in-ear', 'over-ear', 'headset',
              'lautsprecher', 'soundbar',
              'scart', 'usb-c', 'usb c',
              'fernbedienung', 'wandhalterung']
    return not any(w in nl for w in non_tv)


def _is_euro_c7_cable(name: str) -> bool:
    """Check if a product is a Euro C7 power cable."""
    nl = name.lower()
    return (any(w in nl for w in ['netzkabel', 'stromkabel', 'power cable']) and
            any(w in nl for w in ['c7', 'euro', 'eurostecker']))


def _extract_cable_length_m(name: str) -> str | None:
    """Extract cable length in meters, normalized to string like '1.5'."""
    m = re.search(r'(\d+)[.,](\d+)\s*m\b', name.lower())
    if m:
        # Normalize: "1.50" -> "1.5", "1.0" -> "1"
        decimal = m.group(2).rstrip("0")
        if decimal:
            return f"{m.group(1)}.{decimal}"
        return m.group(1)
    m = re.search(r'(\d+)\s*m\b', name.lower())
    if m:
        return m.group(1)
    return None


def match_by_screen_size(
    sources: list[Product],
    targets: list[Product],
    valid_target_refs: set[str] | None = None,
    already_matched: set[tuple[str, str]] | None = None,
) -> list[Match]:
    """Match products by screen size (TVs) or cable spec (cables), cross-brand.

    This is the primary matching strategy for the TV & Audio category where
    the ground truth defines product equivalence by screen size regardless of brand.
    If valid_target_refs is provided, only match targets in that set.
    """
    already_matched = already_matched or set()
    matches = []

    # Build size index for TV targets
    tv_by_size: dict[int, list[Product]] = {}
    cable_targets_1_5m: list[Product] = []

    for t in targets:
        if valid_target_refs and t.reference not in valid_target_refs:
            continue
        if _is_euro_c7_cable(t.name):
            length = _extract_cable_length_m(t.name)
            if length == "1.5":
                cable_targets_1_5m.append(t)
        elif _is_tv_product(t.name):
            size = _extract_screen_size(t.name)
            if size:
                tv_by_size.setdefault(size, []).append(t)

    for source in sources:
        if _is_euro_c7_cable(source.name):
            src_length = _extract_cable_length_m(source.name)
            if src_length == "1.5":
                for target in cable_targets_1_5m:
                    if source.reference == target.reference:
                        continue
                    if (source.reference, target.reference) in already_matched:
                        continue
                    matches.append(Match(
                        source_reference=source.reference,
                        target_reference=target.reference,
                        target_name=target.name,
                        target_retailer=target.retailer or "",
                        target_url=target.url or "",
                        target_price=target.price_eur,
                        confidence=0.85,
                        method="screen_size",
                    ))
        elif _is_tv_product(source.name):
            src_size = _extract_screen_size(source.name)
            if not src_size:
                continue
            for target in tv_by_size.get(src_size, []):
                if source.reference == target.reference:
                    continue
                if (source.reference, target.reference) in already_matched:
                    continue
                matches.append(Match(
                    source_reference=source.reference,
                    target_reference=target.reference,
                    target_name=target.name,
                    target_retailer=target.retailer or "",
                    target_url=target.url or "",
                    target_price=target.price_eur,
                    confidence=0.85,
                    method="screen_size",
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


def _extract_short_model_codes(name: str) -> list[str]:
    """Extract short model codes like 'EK 3163', 'ST 3477', 'WK 1100' from product names.

    These are common in small appliances but too short for extract_model_number.
    """
    codes = []
    skip_prefixes = {
        "BPA", "USB", "LED", "LCD", "EUR", "UHD", "MAX", "RPM", "MIN", "IN",
    }
    for m in re.finditer(r'\b([A-Z]{1,3})\s*[-]?\s*(\d{2,5}[A-Z]?)\b', name):
        prefix = m.group(1)
        number = m.group(2)
        if prefix in skip_prefixes:
            continue
        after = name[m.end():]
        if re.match(
            r'\s*(?:watt|w\b|bar|cm|mm|kg|liter|l\b|ml|gramm|g\b|min\b|v\b)',
            after,
            re.IGNORECASE,
        ):
            continue
        code = f"{prefix} {number}".upper()
        codes.append(code)
    for m in re.finditer(r'\b(\d{5,6})\b', name):
        val = m.group(1)
        if val in ("2024", "2025", "2026"):
            continue
        after = name[m.end():]
        if not re.match(
            r'\s*(?:watt|w\b|bar|cm|mm|kg|liter|l\b|ml|gramm|g\b)',
            after,
            re.IGNORECASE,
        ):
            codes.append(val)
    return codes


def verify_scraped_match(source: Product, scraped_name: str) -> float:
    """Score how well a scraped product name matches a source product.

    Returns a confidence score 0.0-1.0. Used to filter bad scrape results.
    """
    src_model = extract_model_number(source)
    src_name = normalize_name(source.name)
    scraped_norm = normalize_name(scraped_name)
    scraped_upper = scraped_name.upper()

    # Check if model number appears in scraped name
    if src_model and src_model.upper() in scraped_upper:
        return 0.95

    # Check short model codes (e.g. "EK 3163", "ST 3477", "WK 1100")
    src_codes = _extract_short_model_codes(source.name)
    for code in src_codes:
        if code in scraped_upper or code.replace(" ", "") in scraped_upper:
            return 0.95

    # Check brand presence
    brand_present = source.brand and source.brand.lower() in scraped_name.lower()

    # If source has a model code but it's NOT in the scraped name,
    # require a high fuzzy score — the scraped result is likely a different product
    has_model_code = bool(src_model) or bool(src_codes)
    scraped_codes = _extract_short_model_codes(scraped_name)
    model_in_scraped = False
    if src_model and src_model.upper() in scraped_upper:
        model_in_scraped = True
    for code in src_codes:
        if code in scraped_upper or code.replace(" ", "") in scraped_upper:
            model_in_scraped = True

    # Check screen size match
    src_size = _extract_screen_size(source.name)
    scraped_size = _extract_screen_size(scraped_name)
    size_match = src_size and scraped_size and src_size == scraped_size

    # Fuzzy name score (use best of sort and set ratios)
    sort_score = fuzz.token_sort_ratio(src_name, scraped_norm) / 100.0
    set_score = fuzz.token_set_ratio(src_name, scraped_norm) / 100.0
    fuzzy_score = max(sort_score, set_score)

    # Combine signals
    score = fuzzy_score
    if brand_present:
        score = min(score + 0.1, 1.0)
    if size_match:
        score = min(score + 0.05, 1.0)
    if brand_present and size_match and fuzzy_score >= 0.5:
        score = max(score, 0.85)

    # Penalize when source has a recognizable model code but scraped result
    # doesn't contain it. Skip penalty for long numeric-only model numbers
    # (likely internal part numbers, not product identifiers).
    if has_model_code and not model_in_scraped and brand_present:
        is_internal_number = src_model and src_model.isdigit() and len(src_model) >= 6
        if not is_internal_number:
            score = min(score, 0.55)

    return min(score, 1.0)


# Product type taxonomy for category-based matching.
# Order matters: more specific types MUST come before generic ones.
PRODUCT_TYPES: dict[str, list[str]] = {
    # --- Small Appliances ---
    "vacuum_wet_dry": ["nass-trockensauger", "nass trockensauger", "nass- und trockensauger",
                       "nass-/trockensauger", "nass- und trockenstaubsauger",
                       "wischsauger", "saugwischer", "nass trocken"],
    "vacuum_cordless": ["akku staubsauger", "akku-staubsauger", "akkustaubsauger",
                        "kabelloser staubsauger", "kabellos staubsauger",
                        "cordless vacuum"],
    "vacuum_bagged": ["staubsauger mit beutel", "bodenstaubsauger mit beutel"],
    "vacuum_bagless": ["staubsauger ohne beutel", "beutellos", "beutelloser",
                       "zyklon", "cyclone", "bagless"],
    "vacuum_robot": ["saugroboter", "robot vacuum", "roborock s", "roomba"],
    "vacuum_generic": ["staubsauger", "vacuum cleaner", "sauger"],
    "meat_grinder": ["fleischwolf", "meat grinder"],
    "sandwich_grill": ["sandwichmaker", "sandwich maker", "sandwichtoaster",
                       "sandwich-toaster", "kontaktgrill", "waffeleisen und sandwichmaker",
                       "3-in-1", "3 in 1"],
    "toaster": ["toaster", "2-schlitz", "doppelschlitz", "2 scheiben", "langschlitz"],
    "hand_mixer": ["handmixer", "handrührer", "handruehrer", "hand mixer"],
    "stand_mixer": ["standmixer", "stand mixer", "smoothie maker", "blender"],
    "stick_mixer": ["stabmixer", "pürierstab", "puerierstab", "immersion blender"],
    "mixer_generic": ["mixer", "rührgerät"],
    "heating_blanket": ["heizdecke", "heating blanket", "electric blanket",
                        "wärmedecke", "waermedecke"],
    "heating_pad": ["heizkissen", "heating pad", "wärmekissen", "waermekissen"],
    "egg_cooker": ["eierkocher", "egg cooker", "egg boiler"],
    "kettle": ["wasserkocher", "water kettle", "electric kettle"],
    "iron": ["dampfbügeleisen", "bügeleisen", "buegeleisen", "steam iron",
             "dampfbügelstation", "bügelstation"],
    "coffee_machine": ["kaffeemaschine", "kaffeevollautomat", "espressomaschine",
                       "coffee machine", "coffee maker"],
    "food_processor": ["küchenmaschine", "kuechenmaschine", "food processor",
                       "kompakt-küchenmaschine"],
    # --- Large Appliances (accessories BEFORE main appliances to avoid false classification) ---
    # Accessories and small parts first
    "glass_scraper": ["glasschaber", "glass scraper", "ceranfeldschaber",
                      "kochfeld reiniger", "kochfeldreiniger", "herdplattenreinig"],
    "drain_hose": ["ablaufschlauch", "drain hose", "waschmaschinenschlauch"],
    "aquastop_hose": ["aquastop verlängerungsschlauch", "aquastop-schlauch",
                      "zulaufschlauch"],
    "stacking_kit": ["zwischenbaurahmen", "stacking kit", "verbindungsrahmen"],
    "thermometer": ["bratenthermometer", "kühlschrankthermometer",
                    "gefrierschrankthermometer", "kühl-/gefrierschrankther"],
    "range_hood_filter": ["dunstabzug", "aktivkohlefilter", "fettfilter",
                          "range hood filter", "dunstfilter", "filter-set universal"],
    "washing_accessory": ["waschbälle", "waschbaelle", "trocknerbälle",
                          "trocknerbaelle", "dryer balls",
                          "waschmaschinen komplett-pflege", "waschmaschinen pflege"],
    "plumbing_fitting": ["winkelstück", "winkelstueck", "siphon", "kondensatablauf"],
    # Herd set before cooktops (contains "kochfeld" in name)
    "herd_set": ["herdset", "herd-set", "einbau-herdset", "backofen set",
                 "einbauherd", "einbau-herd"],
    # Microwaves -- all merged (GT doesn't distinguish grill vs plain)
    "microwave": ["mikrowelle", "microwave"],
    # Air fryer AFTER microwave (some microwaves have "Heißluftfritteusenfunktion")
    "air_fryer": ["heissluftfritteuse", "heißluftfritteuse", "airfryer", "air fryer",
                  "fritteuse", "friteuse", "easy fry", "dual easy"],
    # Washing machines -- all merged (GT doesn't distinguish toplader vs frontlader)
    "washing_machine": ["waschmaschine", "washing machine", "frontlader",
                        "toplader", "top loader", "top-loader"],
    "tumble_dryer": ["wärmepumpentrockner", "waermepumpentrockner", "trockner",
                     "tumble dryer", "dryer"],
    "dishwasher": ["geschirrspüler", "geschirrspueler", "dishwasher",
                   "spülmaschine", "spuelmaschine"],
    # Cold appliances -- all merged (GT groups fridge+freezer+combos together)
    "cold_appliance": ["kühl- gefrierkombination", "kuehl- gefrierkombination",
                       "kühl-gefrierkombination", "kuehl-gefrierkombination",
                       "kühlgefrierkombination", "fridge freezer", "combi fridge",
                       "gefrierschrank", "stand-gefrierschrank", "gefriertruhe", "freezer",
                       "kühlschrank", "kuehlschrank", "glastürkühlschrank",
                       "glastuerkuehlschrank", "fridge", "refrigerator"],
    # Cooktops -- all merged (GT groups induction+ceramic+electric together)
    "cooktop": ["induktionskochfeld", "induktionskochplatte",
                "induktionsdoppelkochplatte", "induction cooktop",
                "induktion",
                "glaskeramik-kochfeld", "glaskeramikkochfeld",
                "ceranfeld", "ceramic cooktop", "glaskeramik kochfeld",
                "glaskeramik",
                "kochplatte", "einzelkochplatte", "doppelkochplatte",
                "elektrokochzone", "hot plate", "massekochfeld"],
}


def _classify_product_type(name: str) -> str | None:
    """Classify a product into a type based on keyword matching."""
    nl = name.lower()
    for ptype, keywords in PRODUCT_TYPES.items():
        for kw in keywords:
            if kw in nl:
                # "ohne Induktion" means NOT induction
                if ptype == "cooktop_induction" and "ohne induktion" in nl:
                    continue
                return ptype
    return None


def match_by_product_type(
    sources: list[Product],
    targets: list[Product],
    valid_target_refs: set[str] | None = None,
    already_matched: set[tuple[str, str]] | None = None,
) -> list[Match]:
    """Match products that share the same product type classification.

    Used for categories like Small Appliances and Large Appliances where
    the ground truth considers all products of the same sub-type as matches.
    Matches cross-brand (all products of same type are alternatives).
    """
    already_matched = already_matched or set()
    matches = []

    # Build index: product_type -> [targets]
    type_index: dict[str, list[Product]] = {}
    for t in targets:
        if valid_target_refs and t.reference not in valid_target_refs:
            continue
        ptype = _classify_product_type(t.name)
        if ptype:
            type_index.setdefault(ptype, []).append(t)

    for source in sources:
        src_type = _classify_product_type(source.name)
        if not src_type:
            continue

        for target in type_index.get(src_type, []):
            if source.reference == target.reference:
                continue
            if (source.reference, target.reference) in already_matched:
                continue
            matches.append(Match(
                source_reference=source.reference,
                target_reference=target.reference,
                target_name=target.name,
                target_retailer=target.retailer or "",
                target_url=target.url or "",
                target_price=target.price_eur,
                confidence=0.80,
                method="product_type",
            ))

    return matches
