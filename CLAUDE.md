# Product Matcher - Zenline Hackathon

## Context

This is a hackathon project for the Zenline/Anthropic Claude Builders Hackathon. We are vibe coding -- move fast, make decisions, don't overthink it.

**Challenge:** Match 91 source electronics products to equivalent competitor products across 6 Austrian retailers. Scored on precision, recall, and coverage — plus a jury demo evaluating system maturity, UX, reusability, and creativity.

**Team:** Joshua (backend/matching/GPU pipeline) and Diana (frontend/UX/web).

**Scoring platform:** https://hackathon-production-49ca.up.railway.app/ (upload JSON submissions per category)

## Evaluation Criteria (from Zenline)

**The system is 80% of the evaluation. The matching score/leaderboard is only 20%.**

The jury evaluates the **system you build**, not just the matching score. Think of it as building a real product matching tool that could be used in production.

**System Maturity**

- Authentication, proper database, vector/RAG search?
- Which technologies do you use to search & match products?
- How do you handle generic or messy product attributes?

**User Experience**

- Chat-based interface? Smart attribute entry?
- Can you search for any product by any criteria?
- How fast? Start typing and see results immediately?

**Reusability & Flexibility**

- Can you easily upload a new batch and scrape again?
- Adjustable flow? E.g. "Only look for Brand X products"
- Can you iterate back and forth with the results?

**Creativity**

- Surprise us! There is no single right approach.
- Novel matching strategies, clever UX, smart automation
- Think like you're building a real product for a real user.

## Project Structure

- `matcher/` - Core matching logic (Python, backend-only, framework-agnostic)
  - `models.py` - Data models: Product, Match, SubmissionEntry
  - `ean_match.py` - EAN/GTIN exact matching
  - `fuzzy_match.py` - Model number extraction + fuzzy name matching (rapidfuzz)
  - `embedding_match.py` - Semantic matching via sentence-transformers + FAISS (GPU)
  - `vision_match.py` - CLIP image similarity matching (GPU)
  - `claude_verify.py` - Claude API verification of uncertain matches
  - `scraper.py` - Web scraping for 4 hidden retailers
  - `pipeline.py` - Orchestrates all matching strategies end-to-end
- `web/` - Web UI (Diana owns this — placeholder FastAPI app currently here)
- `data/` - Downloaded JSON data from platform (gitignored)
- `output/` - Generated submission JSON files

## Key Commands

```bash
uv sync                          # Install dependencies
uv run python -m matcher.pipeline --sources data/sources.json --targets data/targets.json  # Run pipeline
uv run python -m matcher.pipeline --sources data/sources.json --targets data/targets.json --no-scrape  # Skip scraping
uv run uvicorn web.app:app --reload  # Start web UI
```

## Matching Strategy Priority

1. EAN exact match (highest confidence, ~80% hit rate)
2. Model number extraction + exact match within brand
3. Fuzzy name matching (token_sort_ratio >= 82, same brand)
4. Embedding similarity (multilingual-e5-large, cosine >= 0.85, via FAISS)
5. Vision/CLIP matching (image similarity >= 0.88)
6. Claude Haiku verification for uncertain matches (confidence 0.6-0.9)
7. Web scraping of hidden retailers by EAN then product name

## Hidden Retailers to Scrape

- expert.at
- cyberport.at
- electronic4you.at
- e-tec.at

## Submission Format

Each category gets a separate JSON file uploaded to the platform:

```json
[
  {
    "source_reference": "P_XXXX",
    "competitors": [
      {
        "reference": "P_YYYY",
        "competitor_retailer": "...",
        "competitor_product_name": "...",
        "competitor_url": "...",
        "competitor_price": 99.99
      }
    ]
  }
]
```

Required fields for scoring: `source_reference` and `competitors[].reference`.

## Conventions

- Use `uv` for package management
- Backend matcher code is pure Python — no web framework dependency
- The `web/` directory is Diana's domain — coordinate before changing
- Data files go in `data/` (gitignored), outputs in `output/`
- GPU-heavy work (embeddings, vision) runs on spylab0 server
