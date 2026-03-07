from rapidfuzz import fuzz

from src.models.product import SourceProduct, TargetProduct, CompetitorMatch

SIMILARITY_THRESHOLD = 75.0


def match_by_name(
    source: SourceProduct,
    targets: list[TargetProduct],
    threshold: float = SIMILARITY_THRESHOLD,
) -> list[CompetitorMatch]:
    """Match products using fuzzy string matching on product names."""
    matches = []
    source_name = _normalize(source.name)

    for target in targets:
        target_name = _normalize(target.name)
        score = fuzz.token_sort_ratio(source_name, target_name)

        if score >= threshold:
            matches.append(
                CompetitorMatch(
                    reference=target.reference,
                    competitor_retailer=target.retailer,
                    competitor_product_name=target.name,
                    competitor_url=target.url,
                    competitor_price=target.price,
                    confidence=score / 100.0,
                    match_method="fuzzy_name",
                )
            )

    matches.sort(key=lambda m: m.confidence, reverse=True)
    return matches


def _normalize(name: str) -> str:
    """Normalize product name for comparison."""
    return name.lower().strip()
