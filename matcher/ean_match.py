"""EAN/GTIN exact matching - highest confidence strategy."""

from .models import Match, Product


def _get_eans(product: Product) -> list[str]:
    """Get all EAN/GTIN identifiers for a product."""
    eans = []
    if product.ean:
        eans.append(product.ean.strip())
    specs = product.specifications
    for key in ["GTIN", "EAN-Code", "EAN"]:
        if key in specs and specs[key]:
            val = specs[key].strip()
            if val and val not in eans:
                eans.append(val)
    return [e for e in eans if len(e) >= 8]  # Valid EANs are 8+ digits


def build_ean_index(targets: list[Product]) -> dict[str, list[Product]]:
    """Build a lookup from EAN to target products."""
    index: dict[str, list[Product]] = {}
    for t in targets:
        for ean in _get_eans(t):
            index.setdefault(ean, []).append(t)
    return index


def match_by_ean(sources: list[Product], targets: list[Product]) -> list[Match]:
    """Match source products to targets by exact EAN."""
    ean_index = build_ean_index(targets)
    matches = []

    for source in sources:
        for ean in _get_eans(source):
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
