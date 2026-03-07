# DJ Retail -- Product Matching System (Quick Reference)

## The Problem

- Austrian retailers need to match products across competitors (e.g. "Samsung QE55Q7FAAUXXN" = "Samsung 55 Zoll QLED Q7F Series")
- Different naming conventions, regional model variants, missing barcodes, hidden competitor websites
- Manual matching doesn't scale

## Our Solution: 7-Stage Matching Pipeline

Each stage assigns a confidence score (0--1). Higher-confidence stages run first, later stages skip already-matched pairs.

### Stage 1: EAN Barcode (confidence: 1.0)

- Exact match on EAN (European Article Number) / GTIN (Global Trade Item Number) barcodes -- universal product identifiers
- Checks multiple fields: `specifications.GTIN`, `specifications.EAN-Code`, top-level `ean`
- ~15% hit rate, but 100% confidence when found

### Stage 2: Model Number (confidence: 0.90--0.95)

- Regex (regular expression) extraction from messy product names
- Handles standard codes (`SMS4HVW33E`), short codes (`EK 3163`), Samsung region suffixes (`AUXXN`)
- Skip list filters false positives (`HDR10`, `2025`, `1080p`, `500ml`)
- Matched within same brand only

### Stage 3: Model Series + Size (confidence: 0.85)

- Extracts Samsung series codes (`Q7F` from `QE55Q7FAAUXXN`) + screen size
- Matches same series + same size + same brand across regions

### Stage 4: Product Type (confidence: 0.80)

- 40+ product types with German/English bilingual keywords
- Priority ordering prevents misclassification (e.g. `sandwich_grill` before `toaster`)
- 6 vacuum sub-types, 3 mixer types, heating blanket vs pad, etc.
- **Generalizable:** adding a new category = adding entries to one Python dictionary. When Large Appliances dropped mid-hackathon (44 sources, 3,543 targets), we added ~15 types and had results within the hour
- Falls back to `Produkttyp` spec field when keywords don't match
- Not the only signal -- 6 other stages still work for unknown products

### Stage 5: Fuzzy Matching (confidence: 0.82--0.90)

- Token-sort ratio (sort words alphabetically, then compute edit distance) via RapidFuzz (C++ performance)
- Catches naming variations: "LG 32LQ63806LC" vs "LG 32LQ63006LA"
- 82% threshold, scoped within same brand

### Stage 6: Web Scraping (confidence: 0.60--0.95)

- 4 hidden retailers not in the target pool
- **expert.at** -- parse server-side rendered data directly from HTML
- **electronic4you.at** -- browser impersonation (TLS [Transport Layer Security] fingerprint mimics Chrome)
- **cyberport.at / e-tec.at** -- Cloudflare bypass with rate-limited requests
- Every scraped product verified on multiple signals before acceptance

### Stage 7: Deduplication

- Keep only highest-confidence version of each (source, target) pair

## Architecture

- **Frontend:** React + TypeScript + Vite (fast build tool)
- **Backend:** FastAPI (Python), 15+ REST (Representational State Transfer) endpoints, auto-generated docs at `/docs`
- **Database:** SQLite (lightweight file-based database) with 4 tables (products, matches, scrape_results, pipeline_runs)
- **Auth:** API (Application Programming Interface) key on write endpoints, login modal in sidebar
- **Embeddings:** multilingual-e5-large-instruct (560M parameter AI model), precomputed on GPU (Graphics Processing Unit), FAISS (Facebook AI Similarity Search) index for instant similarity lookups
- **Chat:** Claude Haiku 4.5 (Anthropic's fast, cost-efficient LLM [Large Language Model]) with smart keyword fallback when no API key

## What Makes It Generalizable

- **Category-agnostic** -- zero category-specific code in core matching logic
- **Configurable strategies** -- toggle any of 8 strategies on/off via UI or API (`?strategies=ean,model_number`)
- **Brand filtering** -- `?brand_filter=Tefal` to scope to one manufacturer
- **Upload and re-run** -- POST new JSON batch to `/api/upload`, get matches immediately
- **Match explainability** -- `/api/explain/{src}/{tgt}` shows all matching signals

## Results

| Category         | Recall | Precision | Coverage | Score   |
| ---------------- | ------ | --------- | -------- | ------- |
| TV & Audio       | 100%   | 100%      | 100%     | 50/50   |
| Small Appliances | 99.6%  | 100%      | 100%     | 49.9/50 |
| Large Appliances | 92.9%  | 17.5%     | 100%     | 39.7/50 |

**Total: 174.2/300 -- 1st place** (32 pts ahead of 2nd)

- SA (Small Appliances) and LA (Large Appliances) categories released mid-hackathon, strong results immediately on both
- Same pipeline, no category-specific code

## Key Numbers

| Metric                   | Value                               |
| ------------------------ | ----------------------------------- |
| Leaderboard              | 1st place, 174.2/300 (32 pts ahead) |
| Total matches            | 14,000+ across 3 categories         |
| Matching stages          | 7 in the pipeline                   |
| Hidden retailers scraped | 4                                   |
| API endpoints            | 15+                                 |
| Product types            | 40+ (German/English bilingual)      |

## Technical Highlights

- 7-stage confidence cascade -- higher-confidence stages take priority
- 40+ bilingual product type taxonomy, ordered by specificity
- Real-time web scraping with browser impersonation + multi-signal verification
- Semantic similarity via multilingual sentence embeddings (FAISS index)
- Natural language chat (Claude Haiku 4.5 + smart fallback)
- Full audit trail -- every match records method + confidence, every scrape logged
- API key auth with login UI
- React dashboard with strategy toggles, confidence charts, expandable match details
