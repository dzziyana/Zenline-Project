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

## How We Address "Your System Matters"

The hackathon evaluation weights the system at 80% and the leaderboard score at 20%. Here is how we address every criterion.

### System Maturity

**Authentication** -- The API supports key-based authentication. Write endpoints (run pipeline, upload batches, trigger scrapes) require a valid API key via the `X-Api-Key` header when `MATCHER_API_KEY` is set. Read endpoints stay open. The frontend sidebar has a login modal where users enter their key; it's validated server-side and persisted in the browser for subsequent requests.

**Proper database** -- All data is persisted in SQLite (`data/matcher.db`) with four tables: `products` (source + target products with normalized brands), `matches` (every match with method, confidence, and target metadata), `scrape_results` (raw scraping output for auditing), and `pipeline_runs` (execution history with timestamps and match counts). The pipeline can be re-run without losing previous results.

**Vector/RAG search** -- We precompute multilingual sentence embeddings (multilingual-e5-large-instruct, 560M parameters) on a GPU server and serve them via `/api/similar/{reference}`. This converts product names into numerical vectors so semantically similar products can be found instantly, even across German and English. The FAISS index enables sub-millisecond nearest-neighbor lookups over thousands of products.

**Technologies for search and matching** -- Seven matching strategies in a confidence-weighted cascade: EAN barcode matching, regex-based model number extraction, Samsung model series + screen size matching, keyword-based product type classification (40+ types), fuzzy string matching via RapidFuzz (C++ performance), web scraping with browser impersonation, and semantic embedding similarity. Each stage assigns a confidence score and later stages skip already-matched pairs.

**Handling generic or messy product attributes** -- Brand fields are often empty or use corporate names ("Samsung Electronics GmbH"); we normalize them via a 50+ entry brand map. Model numbers are buried in product names with inconsistent formatting; our regex extractor handles standard codes, short codes, and Samsung region suffixes. Product names mix German and English; our embeddings are multilingual. Specifications use different field names across retailers (`GTIN` vs `EAN-Code` vs `ean`); we check all variants.

### User Experience

**Chat-based interface** -- The Chat page provides natural language product queries powered by Claude Haiku 4.5. Users can ask "show me unmatched Samsung TVs" or "how many matches do we have?" and get formatted answers with product details, match methods, and confidence scores. When no API key is configured, the chat falls back to smart keyword matching that still returns useful results.

**Search for any product by any criteria** -- The Products page has a search bar that accepts any text query. The backend splits multi-word queries into terms and AND-matches each against product names, brands, and EANs. Results can be further filtered by brand dropdown and matched/unmatched status. The API also supports `?brand_filter=`, `?retailer=`, and `?source_only=` parameters.

**Speed -- start typing and see results immediately** -- Product search uses a 300ms debounce: as the user types, results update instantly without pressing Enter. The matching pipeline runs all seven stages in seconds. Dashboard stats and match results load from the database with no delay.

### Reusability and Flexibility

**Upload a new batch and scrape again** -- `POST /api/upload` accepts new source and target JSON files, saves them, runs the full pipeline, and returns matches -- all in one request. No configuration changes needed. The system handled three different product categories (TV & Audio, Small Appliances, Large Appliances) released at different times during the hackathon, producing strong results immediately on each.

**Adjustable flow** -- The Dashboard and Matching pages both have strategy toggle controls. Users can enable or disable any of the eight implemented matching strategies (EAN, Model Number, Model Series, Product Line, Product Type, Screen Size, Fuzzy Name, Web Scrape) before running the pipeline. Three additional strategies (Embedding, Vision/CLIP, LLM Verify) are shown as "coming soon." Brand filtering lets users scope matches to a single manufacturer (e.g. "Only look for Tefal products").

**Iterate back and forth with the results** -- Every match is clickable and expandable. The Matching page shows all matches grouped by source product with confidence bars and method badges. Click "Explain" on any match to see all matching signals (EAN overlap, brand match, model extraction, series codes, screen sizes, fuzzy scores). Re-run the pipeline with different strategy combinations and compare results. Export submission JSON at any time via `/api/submission/download`.

### Creativity

**Multi-strategy confidence cascade** -- Rather than picking one matching algorithm, we run seven in priority order. Each strategy has a confidence range, and higher-confidence matches take precedence. This means we get the precision of barcode matching where available, the recall of fuzzy matching where needed, and the coverage of web scraping for products that only exist on hidden retailers.

**Bilingual product type taxonomy** -- We built a 40+ type classification system with German and English keywords, ordered by specificity to avoid misclassification. For example, "Sandwichtoaster" must match `sandwich_grill` before `toaster`, and "3-in-1 Mikrowelle" must match `microwave` before `sandwich_grill`. This domain knowledge is what makes the system work for real Austrian product data.

**Browser impersonation scraping** -- Four hidden retailers needed four different scraping approaches. We parse server-side rendered data from HTML (expert.at), impersonate Chrome's TLS fingerprint to bypass bot detection (electronic4you.at), and handle Cloudflare protection (cyberport.at, e-tec.at). Every scraped product goes through a multi-signal verification step before acceptance.

**Match explainability** -- Every match in the system is fully transparent. The `/api/explain/{source}/{target}` endpoint shows exactly why two products were linked: which EAN fields matched, whether the brand normalized correctly, what model number was extracted, what series code was found, how similar the fuzzy scores are, and what the final confidence is. Nothing is a black box.

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
