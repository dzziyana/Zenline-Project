"""Claude-based match verification for ambiguous candidates.

Instead of using Claude to find matches (expensive, slow), we use fast
strategies to generate candidates, then Claude verifies the uncertain ones.
"""

from __future__ import annotations

import anthropic

from .models import Match, Product

CLIENT = None


def _get_client() -> anthropic.Anthropic:
    global CLIENT
    if CLIENT is None:
        CLIENT = anthropic.Anthropic()
    return CLIENT


def verify_match(source: Product, target: Product) -> tuple[bool, float]:
    """Ask Claude whether two products are the same.

    Returns (is_match, confidence).
    """
    client = _get_client()

    source_desc = _product_description(source)
    target_desc = _product_description(target)

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=100,
        messages=[{
            "role": "user",
            "content": f"""Are these the same physical product (same manufacturer, same model)?

PRODUCT A:
{source_desc}

PRODUCT B:
{target_desc}

Reply with exactly one of:
- YES (confident match)
- LIKELY (probably the same, minor differences in naming)
- NO (different products)

Then a confidence score 0.0-1.0."""
        }],
    )

    text = response.content[0].text.strip().upper()
    if text.startswith("YES"):
        return True, _parse_confidence(text, default=0.95)
    elif text.startswith("LIKELY"):
        return True, _parse_confidence(text, default=0.8)
    else:
        return False, _parse_confidence(text, default=0.1)


def _product_description(p: Product) -> str:
    """Build a description string for Claude."""
    parts = [f"Name: {p.name}"]
    if p.brand:
        parts.append(f"Brand: {p.brand}")
    if p.ean:
        parts.append(f"EAN: {p.ean}")
    if p.price_eur:
        parts.append(f"Price: EUR {p.price_eur}")
    if p.retailer:
        parts.append(f"Retailer: {p.retailer}")
    for k, v in list(p.specifications.items())[:5]:
        parts.append(f"{k}: {v}")
    return "\n".join(parts)


def _parse_confidence(text: str, default: float) -> float:
    """Extract confidence score from Claude's response."""
    import re
    match = re.search(r'(\d+\.?\d*)', text.split("\n")[-1] if "\n" in text else text[3:])
    if match:
        val = float(match.group(1))
        if 0 <= val <= 1:
            return val
    return default


def verify_batch(
    candidates: list[tuple[Product, Product, Match]],
    min_confidence: float = 0.7,
) -> list[Match]:
    """Verify a batch of candidate matches using Claude.

    candidates: list of (source, target, original_match) tuples
    Returns only verified matches with updated confidence.
    """
    verified = []
    for source, target, match in candidates:
        is_match, confidence = verify_match(source, target)
        if is_match and confidence >= min_confidence:
            match.confidence = confidence
            match.method = f"{match.method}+claude_verified"
            verified.append(match)
    return verified


def filter_uncertain_matches(
    matches: list[Match],
    sources: list[Product],
    targets: list[Product],
    low_threshold: float = 0.6,
    high_threshold: float = 0.9,
) -> list[Match]:
    """Send uncertain matches (between low and high confidence) to Claude for verification.

    Matches above high_threshold are kept as-is.
    Matches below low_threshold are discarded.
    Matches in between are verified by Claude.
    """
    source_map = {p.reference: p for p in sources}
    target_map = {p.reference: p for p in targets}

    certain = []
    to_verify = []

    for m in matches:
        if m.confidence >= high_threshold:
            certain.append(m)
        elif m.confidence >= low_threshold:
            source = source_map.get(m.source_reference)
            target = target_map.get(m.target_reference)
            if source and target:
                to_verify.append((source, target, m))

    if to_verify:
        print(f"Verifying {len(to_verify)} uncertain matches with Claude...")
        verified = verify_batch(to_verify)
        print(f"  {len(verified)} verified as matches")
        certain.extend(verified)

    return certain
