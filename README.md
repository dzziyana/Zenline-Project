# DJ Retail -- Product Matching System

Austrian electronics retailers need to track competitor pricing across hundreds of products. Manually matching "Samsung QE55Q7FAAUXXN" on one site to "Samsung 55 Zoll QLED Q7F Series" on another is tedious, error-prone, and doesn't scale. Different naming conventions, regional model variants, missing barcodes, and hidden competitor websites make this a genuinely hard data problem.

## Our Solution: A Multi-Strategy Matching Pipeline

We built a system that throws every reasonable matching signal at the problem and lets the best one win. Not one algorithm -- a cascade of seven complementary strategies, each catching what the others miss. Each stage assigns a confidence score (0.0--1.0) to every match it produces, and later stages skip pairs that earlier stages already matched. High-confidence signals (like barcodes) always take priority, while fuzzier strategies only fill in the gaps.

### The Pipeline

1. **EAN Exact Match** (confidence: 1.0) -- Barcode matching. When two products share an EAN, they're the same product. Checks `specifications.GTIN`, `specifications.EAN-Code`, and the top-level `ean` field since retailers store barcodes differently.

2. **Model Number Extraction** (confidence: 0.90--0.95) -- Regex-based extraction of model numbers from messy product names. Handles standard codes (`SMS4HVW33E`), short codes (`EK 3163`), and Samsung region suffix stripping (`AUXXN`, `AAUXXN`). Maintains a skip list to filter false positives like `HDR10`, `2025`, `1080p`.

3. **Model Series + Size** (confidence: 0.85) -- Extracts Samsung TV series codes (`Q7F` from `QE55Q7FAAUXXN`) and screen sizes. Matches products sharing the same series, size, and brand across different regional model numbers.

4. **Product Type Classification** (confidence: 0.80) -- Keyword-based taxonomy with 40+ product types in German and English. Ordered by specificity (e.g. `sandwich_grill` before `toaster`, accessories before main appliances). Handles small appliances, large appliances, and electronics.

5. **Fuzzy Model + Name Matching** (confidence: 0.82--0.90) -- Token-sort ratio via RapidFuzz, scoped within the same brand. Catches naming variations like "LG 32LQ63806LC" vs "LG 32LQ63006LA".

6. **Web Scraping** (confidence: 0.60--0.95) -- Scrapes four hidden retailer websites not in the provided target pool. Each site needed a tailored approach: server-side rendered data extraction (expert.at), browser impersonation (electronic4you.at), and Cloudflare bypass (cyberport.at, e-tec.at). Every scraped product is verified against the source before acceptance.

7. **Deduplication** -- Multiple strategies may find the same pair. We keep only the highest-confidence version.

### What Makes It Generalizable

- **Category-agnostic**: Adding a new product category means adding keywords to the `PRODUCT_TYPES` dictionary. All matching stages, scoring, and submission logic are reusable.
- **Configurable strategies**: Run only specific stages via `?strategies=ean,model_number,product_type`.
- **Brand filtering**: Scope to just one manufacturer with `?brand_filter=Tefal`.
- **Upload and re-run**: POST new source/target JSON batches to `/api/upload` and get matches immediately.
- **Chat interface**: Natural language product queries powered by Claude Haiku with smart keyword fallback.
- **Match explainability**: Every match can be inspected via `/api/explain/{source}/{target}` showing all matching signals.
- **Authentication**: API key-based auth on write endpoints. Set `MATCHER_API_KEY` environment variable to enable. Login UI in the sidebar.

### Results

| Category         | Sources | Matching Score | Scraping Score | Total    |
| ---------------- | ------- | -------------- | -------------- | -------- |
| TV & Audio       | 17      | 50/50          | 23.8/50        | 73.8/100 |
| Small Appliances | 29      | 49.9/50        | 10.8/50        | 60.7/100 |
| Large Appliances | 44      | 39.7/50        | 0/50           | 39.7/100 |

**Total: 174.2/300 -- 1st place** (32 points ahead of 2nd)

The system handles three very different product categories -- consumer electronics (model numbers), kitchen appliances (product types), and large household appliances (cross-brand type matching) -- using the same pipeline with zero category-specific code in the core matching logic.

## Quick Start

```bash
# Install dependencies
uv sync

# Start the web application
uv run python -m uvicorn matcher.api:app --port 8001

# Open in browser
open http://localhost:8001
```

### Running the Pipeline

```bash
# Run matching for a category
uv run python -m matcher.pipeline \
  --sources data/source_products_tv_audio.json \
  --targets data/target_products_tv_audio.json \
  --output output/submission_tv_audio.json \
  --category "TV & Audio"

# Skip web scraping (faster, for testing)
uv run python -m matcher.pipeline --sources data/sources.json --targets data/targets.json --no-scrape

# Submit results to the platform
uv run python scripts/submit.py "TV & Audio"
uv run python scripts/submit.py "Small Appliances"
uv run python scripts/submit.py "Large Appliances"
```

### Using the Web Interface

The web UI provides:

- **Dashboard** with stats, method breakdown, confidence distribution, and brand analysis
- **Products** page with search, filtering, and per-product detail pages showing all matches
- **Matching** page to run the pipeline live and inspect results with expandable match details
- **Scraping** page to view and trigger live scrapes of hidden retailers
- **Chat** interface for natural language product queries

### API Endpoints

The full API is documented at `http://localhost:8001/docs` (auto-generated OpenAPI/Swagger). Key endpoints:

- `POST /api/match/{category}` -- Run pipeline on demand
- `GET /api/search?q=samsung` -- Full-text product search
- `POST /api/chat` -- Natural language queries (Claude Haiku)
- `POST /api/upload` -- Upload new source/target JSON batches
- `POST /api/scrape/{reference}` -- Live scrape hidden retailers
- `GET /api/explain/{src}/{tgt}` -- Match explanation with all signals
- `GET /api/dashboard` -- Real-time stats and method breakdown
- `GET /api/similar/{ref}` -- Semantic similarity via precomputed embeddings
- `GET /api/submission/download` -- Export results as JSON file

---

## Technical Details

### Architecture

```
React Frontend (TypeScript)
    |
    v
FastAPI Backend (port 8001)
    |
    v
SQLite Database (data/matcher.db)
    |-- products        Source + target products with normalized brands
    |-- matches         Every match with method, confidence, target metadata
    |-- scrape_results  Raw scraping output for auditing
    |-- pipeline_runs   Execution history (category, timestamp, match counts)
```

### Project Structure

```
matcher/                 # Core matching logic (Python, framework-agnostic)
  api.py                 # FastAPI REST API + chat endpoints (15+ endpoints)
  pipeline.py            # Orchestrates all matching strategies
  models.py              # Data models (Product, Match, SubmissionEntry)
  ean_match.py           # EAN/GTIN exact matching
  fuzzy_match.py         # Model number extraction, fuzzy matching, product type classification
  embedding_match.py     # Semantic matching (sentence-transformers + FAISS)
  vision_match.py        # CLIP image similarity matching
  claude_verify.py       # Claude API verification of uncertain matches
  scraper.py             # Web scraping for 4 hidden retailers
  db.py                  # SQLite backend with full audit trail
webapp/                  # React frontend (TypeScript)
scripts/                 # Submission and utility scripts
data/                    # Downloaded JSON data (gitignored)
output/                  # Generated submission files
```

### Key Technical Decisions

- **Confidence cascade**: Higher-confidence strategies run first and their matches are skipped by later stages. EAN (1.0) > model number (0.95) > model series (0.85) > product type (0.80) > fuzzy (0.82) > scraping (0.60--0.95).

- **Product type taxonomy ordering**: The classifier returns the first matching type, so specific types must appear before generic ones. For example, `sandwich_grill` before `toaster` (because "Sandwichtoaster" contains "toaster"), `glass_scraper` before `cooktop` (because "Glasschaber fur Glaskeramik-Kochfelder" contains "Kochfeld").

- **Region suffix stripping**: Samsung encodes sales regions in model numbers (`QE55Q7FAAUXXN` in Austria vs `QE55Q7FAMTXZT` in Italy). We strip these suffixes to match cross-market variants.

- **Scraping verification**: Every scraped product is scored on multiple signals (brand match, model number match, screen size proximity, name similarity). Only matches above 0.6 are accepted. This eliminates false positives like "same brand, completely wrong product."

- **Semantic embeddings**: Multilingual-e5-large-instruct (560M parameters) converts product names into vectors. Precomputed on GPU, used for instant "find similar products" lookups. Supplementary discovery tool alongside the main pipeline.

### Dependencies

- Python 3.11+ with `uv` for package management
- `rapidfuzz` for high-performance fuzzy string matching
- `httpx` + `curl_cffi` for web scraping with browser impersonation
- `sentence-transformers` + `faiss-cpu` for embedding-based similarity
- `fastapi` + `uvicorn` for the REST API
- React + TypeScript + Vite for the frontend
