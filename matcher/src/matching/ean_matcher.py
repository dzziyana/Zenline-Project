from src.models.product import SourceProduct, TargetProduct, CompetitorMatch


def match_by_ean(
    source: SourceProduct, targets: list[TargetProduct]
) -> list[CompetitorMatch]:
    """Match products by exact EAN/GTIN barcode. Highest confidence method."""
    if not source.ean:
        return []

    matches = []
    for target in targets:
        if target.ean and source.ean.strip() == target.ean.strip():
            matches.append(
                CompetitorMatch(
                    reference=target.reference,
                    competitor_retailer=target.retailer,
                    competitor_product_name=target.name,
                    competitor_url=target.url,
                    competitor_price=target.price,
                    confidence=1.0,
                    match_method="ean",
                )
            )
    return matches
