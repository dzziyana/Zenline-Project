import json
import os

from openai import OpenAI

from src.models.product import SourceProduct, TargetProduct, CompetitorMatch

client: OpenAI | None = None


def get_client() -> OpenAI:
    global client
    if client is None:
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return client


def match_with_llm(
    source: SourceProduct,
    candidates: list[TargetProduct],
    max_candidates: int = 20,
) -> list[CompetitorMatch]:
    """Use an LLM to evaluate candidate matches and pick the best ones."""
    if not candidates:
        return []

    top_candidates = candidates[:max_candidates]
    candidate_descriptions = []
    for i, c in enumerate(top_candidates):
        desc = f"{i}: ref={c.reference}, name={c.name}"
        if c.brand:
            desc += f", brand={c.brand}"
        if c.ean:
            desc += f", ean={c.ean}"
        candidate_descriptions.append(desc)

    source_desc = f"name={source.name}"
    if source.brand:
        source_desc += f", brand={source.brand}"
    if source.ean:
        source_desc += f", ean={source.ean}"

    prompt = f"""You are a product matching expert for electronics retailers.

Source product: {source_desc}

Candidate target products:
{chr(10).join(candidate_descriptions)}

Which candidates are the SAME product as the source? Consider brand, model number, and specifications.
Return a JSON array of indices (0-based) of matching candidates. Return [] if none match.
Only return exact product matches, not similar products.

Response format: [0, 3, 7] or []"""

    try:
        response = get_client().chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=200,
        )
        content = response.choices[0].message.content.strip()
        indices = json.loads(content)

        matches = []
        for idx in indices:
            if 0 <= idx < len(top_candidates):
                target = top_candidates[idx]
                matches.append(
                    CompetitorMatch(
                        reference=target.reference,
                        competitor_retailer=target.retailer,
                        competitor_product_name=target.name,
                        competitor_url=target.url,
                        competitor_price=target.price,
                        confidence=0.85,
                        match_method="llm",
                    )
                )
        return matches
    except Exception:
        return []
