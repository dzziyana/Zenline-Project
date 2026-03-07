"""EAN/GTIN exact matching - highest confidence strategy."""

from .models import Match, Product


def build_ean_index(targets: list[Product]) -> dict[str, list[Product]]:
    """Build a lookup from EAN to target products."""
    index: dict[str, list[Product]] = {}
    for t in targets:
        if t.ean:
            ean = t.ean.strip()
            if ean:
                index.setdefault(ean, []).append(t)
    return index


def match_by_ean(sources: list[Product], targets: list[Product]) -> list[Match]:
    """Match source products to targets by exact EAN."""
    ean_index = build_ean_index(targets)
    matches = []

    for source in sources:
        if not source.ean:
            continue
        ean = source.ean.strip()
        if ean in ean_index:
            for target in ean_index[ean]:
                matches.append(Match(
                    source_reference=source.reference,
                    target_reference=target.reference,
                    target_name=target.name,
                    target_retailer=target.retailer or "",
                    target_url=target.url or "",
                    target_price=target.price_eur,
                    confidence=1.0,
                    method="ean",
                ))

    return matches
