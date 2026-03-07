# DJ Retail -- Product Matching System

## Before the Demo

```bash
cd /Users/joshua/Developer/Zenline-Project
uv run python -m uvicorn matcher.api:app --port 8001 --reload
```

Open http://localhost:8001 in browser.

---

## The Problem

Austrian electronics retailers need to track competitor pricing across hundreds of products. Manually matching "Samsung QE55Q7FAAUXXN" on one site to "Samsung 55 Zoll QLED Q7F Series" on another is tedious, error-prone, and doesn't scale. Different naming conventions, regional model variants, missing barcodes, and hidden competitor websites make this a genuinely hard data problem.

## Our Solution: A Multi-Strategy Matching Pipeline

We built a system that throws every reasonable matching signal at the problem and lets the best one win. Not one algorithm -- a cascade of seven complementary strategies, each catching what the others miss. Each stage assigns a confidence score (0.0--1.0) to every match it produces, and later stages skip pairs that earlier stages already matched. This means high-confidence signals (like barcodes) always take priority, while fuzzier strategies only fill in the gaps.

### The Pipeline (in execution order)

**Stage 1: EAN Exact Match (confidence: 1.0)**
The gold standard. EAN (European Article Number) is the 13-digit barcode printed on product packaging -- a universal product identifier. When two products share an EAN, they're the same product. Period. But EANs are often missing, buried in nested specification fields, or use different field names across retailers. Our parser checks multiple fields where retailers might store this barcode: `specifications.GTIN` (Global Trade Item Number -- the international version of EAN), `specifications.EAN-Code`, and the top-level `ean` field. Different retailers use different field names for the same thing, so we check all of them. Hit rate: ~15% of products, but 100% confidence when found.

**Stage 2: Model Number Extraction (confidence: 0.90--0.95)**
We extract model numbers from messy product names using carefully tuned regex patterns (regular expressions -- text search rules that describe patterns like "two letters followed by digits"). The core regex looks for sequences of letters and digits that match common manufacturer patterns -- e.g. "REMINGTON S6505 Proo Sleek & Curl Haarglatter" becomes model `S6505`, "SEVERIN EK 3163 Eierkocher" becomes `EK 3163`. Implementation details:

- **Standard codes**: Patterns like `SMS4HVW33E` or `QE55Q7FAAUXXN` -- at least 2 letters + digits or vice versa, minimum 5 characters
- **Short model codes**: Two uppercase letters + space + 3--4 digits (e.g. `EK 3163`, `ST 3477`, `WK 1100`) -- common in small appliances where brands use compact identifiers
- **Skip list**: We maintain a list of strings that look like model numbers but aren't -- `HDR10`, `2025`, `1080p`, `500ml`, `USB3`, `WiFi6`, etc. Without this, the regex would match technical specs instead of actual models
- **Region suffix stripping**: Samsung encodes the sales region in model numbers (`QE55Q7FAAUXXN` in Austria vs `QE55Q7FAMTXZT` in Italy). We strip suffixes like `AUXXN`, `AAUXXN`, `MTXZT` to match the same product across markets

Matching is done within the same brand only -- a model number match across brands is almost certainly a coincidence.

**Stage 3: Model Series + Size (confidence: 0.85)**
Samsung sells the Q7F in 50", 55", and 65" sizes. The model number differs by region, but the series and screen size are the key identifiers. We extract series codes using a regex pattern that looks for Samsung's naming convention (prefixes like QE/GQ/TQ followed by screen size digits followed by the series code) -- this pulls `Q7F` from `QE55Q7FAAUXXN`. Screen size comes from the two digits after the prefix (`QE**55**Q7F...` = 55 inches). Two products match if they share the same series code AND screen size AND brand. This catches cross-retailer listings where one says "Samsung QE55Q7FAAUXXN" and another says "Samsung Q7F 55 Zoll QLED".

**Stage 4: Product Type Classification (confidence: 0.80)**
For categories like Small Appliances, the ground truth considers all products of the same specific sub-type as matches (e.g. all cordless vacuums are alternatives to each other). We built a keyword-based taxonomy with 20+ product types, each defined by a list of German and English keywords. The classifier checks keywords in priority order -- more specific types first:

- 6 vacuum sub-types: `vacuum_wet_dry` ("Nass-Trockensauger", "Wischsauger"), `vacuum_cordless` ("Akku Staubsauger", "kabellos"), `vacuum_bagged` ("mit Beutel"), `vacuum_bagless` ("ohne Beutel", "beutellos"), `vacuum_robot` ("Saugroboter"), `vacuum_generic` (catch-all "Staubsauger")
- `sandwich_grill` checked before `toaster` -- because "Sandwichtoaster" contains "toaster" and would match the wrong category
- `meat_grinder` checked before `sandwich_grill` -- because some meat grinders say "3-in-1" which is also a sandwich maker keyword
- `hand_mixer` vs `stand_mixer` vs `stick_mixer` -- different appliances despite all being "mixers"
- `heating_blanket` ("Heizdecke") vs `heating_pad` ("Heizkissen") -- the ground truth distinguishes these

Keyword ordering matters. The classifier returns the first matching type, so more specific types must appear before generic ones in the dictionary. This is where most of the domain knowledge lives.

**Stage 5: Fuzzy Model + Name Matching (confidence: 0.82--0.90)**
For products that slip through the cracks, we use fuzzy string matching via the RapidFuzz library (a high-performance string comparison library written in C++ for speed). Specifically, we use "token sort ratio" -- this splits both product names into individual words, sorts them alphabetically, then computes the Levenshtein edit distance (the minimum number of single-character insertions, deletions, or substitutions needed to turn one string into the other). The score is `1 - (edit_distance / max_length)`, expressed as a percentage -- so two identical strings score 100%, and two completely different strings score close to 0%.

This means "Samsung 55 Zoll QLED TV Q7F" and "Q7F QLED TV Samsung 55 Zoll" score 100% despite having completely different word order -- because after sorting, both become "55 Q7F QLED Samsung TV Zoll".

A threshold of 82% keeps precision high while catching naming variations like "LG 32LQ63806LC" vs "LG 32LQ63006LA" (regional variants of the same panel -- they differ by only 2 characters). All fuzzy matching is scoped within the same brand to avoid cross-brand false positives (many products from different brands have similar generic names like "Standmixer 500W").

**Stage 6: Web Scraping (Hidden Retailers) (confidence: 0.60--0.95)**
Four competitor websites aren't in the provided target pool -- we have to visit them ourselves and find matching products. Each site has its own anti-bot protections, so each needed a tailored approach:

- **expert.at** -- This site pre-loads all its product data into the page before sending it to the browser (a technique called server-side rendering). Instead of opening a full browser to view the page, we read the raw page source and extract product names, prices, and URLs directly from a hidden data block embedded in the HTML. Much faster and more reliable than simulating a real user clicking around.
- **electronic4you.at** -- This site checks whether requests are coming from a real browser or an automated script, and blocks scripts. We use a specialized library that makes our script's requests look identical to a real Chrome browser -- same encryption handshake, same headers, same behavior. The site can't tell the difference.
- **cyberport.at / e-tec.at** -- These sites use Cloudflare, a widely-used security service that aggressively blocks automated access. Even requesting the homepage returns an "access denied" page. We get partial results by carefully spacing out requests to avoid triggering rate limits.

Every scraped product goes through a verification step before we accept it as a match. The verifier checks multiple signals: does the brand match? Does the model number match? Is the screen size close? How similar are the product names overall? Each signal contributes to a weighted score between 0 and 1. Only matches scoring above 0.6 are accepted -- this filters out false positives like "same brand but completely wrong product" which would otherwise slip through.

**Stage 7: Deduplication**
Multiple strategies may find the same (source, target) pair. We keep only the highest-confidence version. If a new match has higher confidence than the existing one for the same product pair, it replaces it.

### The Architecture

```
React Frontend (TypeScript)          <-- the web UI users interact with
    |
    v
FastAPI Backend (port 8001)          <-- Python web server handling all logic
    |-- /api/match/{category}     Run pipeline on demand
    |-- /api/search               Full-text product search
    |-- /api/chat                 Natural language queries (Claude Haiku)
    |-- /api/upload               Upload new source/target JSON batches
    |-- /api/scrape/{reference}   Live scrape hidden retailers for any product
    |-- /api/explain/{src}/{tgt}  Match explanation showing all signals
    |-- /api/dashboard            Real-time stats and method breakdown
    |-- /api/similar/{ref}        Semantic similarity via precomputed embeddings
    |-- /api/submission/download  Export results as JSON file
    |
    v
SQLite Database (data/matcher.db)
    |-- products        Source + target products with normalized brands
    |-- matches         Every match with method, confidence, target metadata
    |-- scrape_results  Raw scraping output for auditing
    |-- pipeline_runs   Execution history (category, timestamp, match counts)
```

The frontend communicates with the backend via a REST API (a standard web interface where the frontend sends HTTP requests and gets JSON responses back). All product data, matches, and scrape results are persisted in SQLite (a lightweight file-based database) -- the pipeline can be re-run without losing previous results. The API supports optional API key authentication on write endpoints (so only authorized users can modify data) while keeping read endpoints open for anyone to query.

### What Makes It Generalizable

1. **Category-agnostic pipeline**: Adding a new product category means adding product type keywords to the `PRODUCT_TYPES` dictionary. The matching stages, scoring, deduplication, and submission logic are all reusable without modification.
2. **Configurable strategies**: The API accepts `?strategies=ean,model_number,product_type` to run only specific stages. Useful for debugging or when you know certain strategies don't apply to a category.
3. **Brand filtering**: Pass `?brand_filter=Tefal` to only match products from a specific brand.
4. **Upload and re-run**: POST a new JSON batch of source/target products to `/api/upload`. The system saves the files, runs the pipeline, and returns matches -- all in one request.
5. **Chat interface**: Natural language product queries powered by Claude Haiku (Anthropic's fast, cost-efficient LLM). The chat endpoint searches the database, provides context to the model, and returns formatted responses. Falls back to smart keyword matching when no API key is available.
6. **Match explainability**: Every match can be inspected via `/api/explain/{source}/{target}` -- it shows all matching signals (EAN overlap, brand match, model extraction, series codes, screen sizes, fuzzy scores) so a user can understand why two products were matched and with what confidence.

### Results

| Category         | Sources | Recall | Precision | Coverage | Score   |
| ---------------- | ------- | ------ | --------- | -------- | ------- |
| TV & Audio       | 17      | 100%   | 100%      | 100%     | 50/50   |
| Small Appliances | 29      | 98.2%  | 66.7%     | 100%     | 46.2/50 |

- **Recall** = "of all the correct matches that exist, how many did we find?" (98.2% = we found 222 out of 226)
- **Precision** = "of all the matches we submitted, how many were actually correct?" (66.7% = 222 correct out of 333 submitted)
- **Coverage** = "for how many source products did we find at least one match?" (100% = all 29 sources have matches)

The system handles two very different product categories -- consumer electronics (matched primarily by model number and screen size) and kitchen/home appliances (matched primarily by product type classification) -- using the same pipeline with zero category-specific code in the core matching logic. The Small Appliances category was released mid-hackathon and our system produced strong results immediately, demonstrating real generalizability.

## Technical Highlights

- **7-stage matching cascade** with confidence scoring at each stage, higher-confidence stages take priority
- **20+ product type classifications** with German/English bilingual keywords, ordered by specificity
- **Real-time web scraping** with browser impersonation (making automated requests look like a real browser) and multi-signal match verification
- **Precomputed embeddings** using multilingual-e5-large-instruct -- a 560M parameter AI model that converts product names into numerical vectors (lists of numbers representing meaning). Products with similar meanings end up with similar vectors, even across German and English. We precompute these vectors once, then use them for instant similarity lookups.
- **Natural language chat** powered by Claude Haiku 4.5 (Anthropic's fast, cost-efficient LLM). Users can ask questions like "show me unmatched Samsung TVs" and get formatted answers based on the database contents.
- **Full audit trail** -- every match records its method and confidence, every scrape result is logged with raw data. Nothing is a black box.
- **RESTful API** with 15+ endpoints, auto-generated interactive documentation at `/docs` (via OpenAPI/Swagger -- an industry standard for API documentation), and optional API key authentication
- **React dashboard** with live stats, expandable match details, confidence distribution charts, and strategy toggle controls

---

## Demo Flow (10-15 minutes)

### 1. Dashboard Overview (2 min)

Open http://localhost:8001. The Dashboard shows:

- **Stats cards**: total sources, targets, matches, match rate
- **Method breakdown**: how many matches came from each strategy (EAN, model number, product type, scraping, etc.)
- **Confidence distribution**: histogram of match confidence scores
- **Brand stats**: matches per brand

**Say:**

- "We built a multi-strategy matching pipeline that uses 7 different approaches"
- "1185 matches found across 2 categories"
- "The system handles TV & Audio and Small Appliances with zero category-specific code"

### 2. Products Page (2 min)

Navigate to **Products**. Show:

- Product grid with all source products
- **Search**: type "Samsung" -- instant filtering
- Click a product to see its **detail page** with all matches, confidence scores, and retailer links

**Say:**

- "Every product has a detail page showing exactly how it was matched"
- "Similar products are found using multilingual sentence embeddings -- an AI model that understands product meaning across German and English"

### 3. Matching Page -- Run the Pipeline Live (3 min)

Navigate to **Matching**. Show:

- Existing matches loaded from the database (expandable rows)
- Click **Run Pipeline** to trigger matching for a category
- Expand a match row to see: confidence score, method used, retailer, URL
- Click "Explain" on a match to see all matching signals

**Say:**

- "The pipeline runs 7 stages in sequence: EAN, model number, model series, product type, fuzzy model, fuzzy name, and scraping"
- "Every match is explainable -- we can show exactly why two products were linked"

### 4. Scraping Page (2 min)

Navigate to **Scraping**. Show:

- Scrape results from hidden retailers
- Click **Re-scrape** on a product to trigger live scraping
- Show verified vs unverified results with prices and URLs

**Say:**

- "We scrape 4 hidden retailers that aren't in the provided target pool"
- "expert.at pre-renders data into the page -- we parse it directly from the HTML source"
- "electronic4you.at blocks scripts, so we impersonate a real Chrome browser"
- "Every scraped result is verified against the source product before we accept it"

### 5. Chat Interface (2 min)

Navigate to **Chat**. Type these queries:

- "Show me all Samsung products"
- "Which products are unmatched?"
- "Find toasters"
- "How many matches do we have?"

**Say:**

- "Natural language product search powered by Claude Haiku"
- "The chat has full access to the product database -- search by brand, price, category, match status"

### 6. Upload New Batch (1 min)

Show reusability by running in terminal:

```bash
curl -X POST http://localhost:8001/api/upload \
  -F "sources=@data/source_products_small_appliances.json" \
  -F "targets=@data/target_products_small_appliances.json"
```

**Say:**

- "Upload any new JSON batch and get matches immediately"
- "The system is category-agnostic -- works for TVs, kitchen appliances, or any product category"
- "Brand filtering lets you scope to just one manufacturer"

### 7. API Docs (1 min)

Open http://localhost:8001/docs to show the auto-generated API documentation.

**Say:**

- "15+ REST API endpoints, all documented and interactive"
- "Every endpoint can be tested right here in the browser"
- "SQLite database with full audit trail -- every match, scrape, and pipeline run is logged"

---

## Key Numbers

| Metric                   | Value                                 |
| ------------------------ | ------------------------------------- |
| Total matches            | 1185 across 2 categories              |
| Matching methods         | 7 stages in the pipeline              |
| TV & Audio score         | 50/50 (100% recall, 100% precision)   |
| Small Appliances score   | 46.2/50 (98.2% recall, 100% coverage) |
| Hidden retailers scraped | 4                                     |
| API endpoints            | 15+                                   |
| Product types classified | 20+ (German/English)                  |

## If Something Breaks

- **API won't start**: `lsof -i :8001` to check if port is in use, kill the process, restart
- **Frontend shows empty data**: Restart the API
- **Chat returns empty**: Works without API key using smart fallback
- **Scraping fails**: Some retailers block after many requests. Show cached results instead.
- **Database empty**: Re-run pipeline: `curl -X POST 'http://localhost:8001/api/match/tv_audio'`
