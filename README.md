# Zenline-Project

Electronics competitor product matching tool for the Zenline hackathon challenge.

## What This Does

We have 91 source products from an Austrian electronics retailer. The goal is to match them to equivalent products sold by competitors — both from a provided target pool (2 visible retailers) and by scraping 4 additional retailer websites.

## Architecture

```
                    ┌─────────────────────────────────┐
                    │         Source Products          │
                    │    (91 products, 3 categories)   │
                    └────────────┬────────────────────┘
                                 │
                    ┌────────────▼────────────────────┐
                    │       Matching Pipeline          │
                    │                                  │
                    │  1. EAN exact match              │
                    │  2. Model number extraction      │
                    │  3. Fuzzy name matching          │
                    │  4. Embedding similarity (GPU)   │
                    │  5. Vision/CLIP matching (GPU)   │
                    │  6. Claude verification          │
                    │  7. Web scraping (4 retailers)   │
                    └────────────┬────────────────────┘
                                 │
                    ┌────────────▼────────────────────┐
                    │      submission.json             │
                    │  (upload to Zenline platform)    │
                    └─────────────────────────────────┘
```

### Matching Strategies (in priority order)

1. **EAN matching** — Exact barcode match. Highest confidence (~80% hit rate).
2. **Model number matching** — Extract model numbers (e.g. "SMS4HVW33E") and match within same brand.
3. **Fuzzy name matching** — Token-sort ratio on normalized product names within same brand.
4. **Embedding matching** — Encode products with multilingual-e5 model, find nearest neighbors via FAISS. Catches semantic matches that string matching misses. Runs on GPU (spylab0).
5. **Vision matching** — CLIP image embeddings for visual similarity. Same product looks the same regardless of name. Runs on GPU (spylab0).
6. **Claude verification** — For uncertain matches (confidence 0.6-0.9), ask Claude Haiku to verify "are these the same product?"
7. **Web scraping** — Search hidden retailer websites (expert.at, cyberport.at, electronic4you.at, e-tec.at) by EAN and product name.

### Project Structure

```
matcher/             # Core matching logic (backend, framework-agnostic)
  models.py          # Data models (Product, Match, SubmissionEntry)
  ean_match.py       # EAN/GTIN exact matching
  fuzzy_match.py     # Model number + fuzzy name matching (rapidfuzz)
  embedding_match.py # Semantic embedding matching (sentence-transformers + FAISS)
  vision_match.py    # CLIP image matching
  claude_verify.py   # Claude API verification of ambiguous matches
  scraper.py         # Web scraping for hidden retailers
  pipeline.py        # Orchestrates all strategies
web/                 # Web UI (placeholder — Diana owns this)
  app.py             # Basic FastAPI demo interface
data/                # Downloaded JSON data (gitignored)
output/              # Generated submission files
```

## Setup

```bash
# Install dependencies
uv sync

# Run the matching pipeline (once you have data downloaded)
uv run python -m matcher.pipeline --sources data/source_products.json --targets data/target_pool.json --output output/submission.json

# Run without scraping (faster, for testing)
uv run python -m matcher.pipeline --sources data/source_products.json --targets data/target_pool.json --no-scrape

# Start web UI
uv run uvicorn web.app:app --reload
```

## GPU Components (spylab0)

The embedding and vision matching modules need GPU. To precompute embeddings on spylab0:

```bash
# Precompute text embeddings
uv run python -m matcher.embedding_match --input data/source_products.json --output data/source_embeddings
uv run python -m matcher.embedding_match --input data/target_pool.json --output data/target_embeddings

# Precompute image embeddings (after downloading images)
uv run python -m matcher.vision_match --image-dir data/source_images --output data/source_image_embeddings
uv run python -m matcher.vision_match --image-dir data/target_images --output data/target_image_embeddings
```

## Data Flow

1. Download source products + target pool JSON from the [Zenline platform](https://hackathon-production-49ca.up.railway.app/)
2. Put them in `data/`
3. Run the pipeline
4. Upload `output/submission.json` back to the platform for scoring
5. Iterate!
