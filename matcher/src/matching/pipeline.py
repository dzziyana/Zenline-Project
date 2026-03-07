from src.models.product import (
    SourceProduct,
    TargetProduct,
    CompetitorMatch,
    SourceProductSubmission,
)
from src.matching.ean_matcher import match_by_ean
from src.matching.fuzzy_matcher import match_by_name
from src.matching.llm_matcher import match_with_llm


def run_matching_pipeline(
    sources: list[SourceProduct],
    targets: list[TargetProduct],
    use_llm: bool = False,
    fuzzy_threshold: float = 75.0,
) -> list[SourceProductSubmission]:
    """Run the full matching pipeline: EAN -> Fuzzy -> LLM."""
    results = []

    for source in sources:
        all_matches: dict[str, CompetitorMatch] = {}

        # Stage 1: EAN matching (highest confidence)
        ean_matches = match_by_ean(source, targets)
        for m in ean_matches:
            all_matches[m.reference] = m

        # Stage 2: Fuzzy name matching
        fuzzy_matches = match_by_name(source, targets, threshold=fuzzy_threshold)
        for m in fuzzy_matches:
            if m.reference not in all_matches:
                all_matches[m.reference] = m

        # Stage 3: LLM matching (optional, for ambiguous cases)
        if use_llm and len(all_matches) == 0:
            # Pre-filter candidates by brand for efficiency
            brand_candidates = [
                t
                for t in targets
                if source.brand
                and t.brand
                and source.brand.lower() == t.brand.lower()
            ]
            if not brand_candidates:
                brand_candidates = targets

            llm_matches = match_with_llm(source, brand_candidates)
            for m in llm_matches:
                if m.reference not in all_matches:
                    all_matches[m.reference] = m

        results.append(
            SourceProductSubmission(
                source_reference=source.reference,
                competitors=list(all_matches.values()),
            )
        )

    return results
