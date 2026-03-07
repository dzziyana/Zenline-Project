# Coordination Board

Shared board for all Claude instances on this project. READ THIS FIRST before doing any work.

**Protocol:**

- Read this file before starting work
- Claim a task by writing your session info next to it
- Update status when done -- move task to DONE with a summary of what changed
- Post findings, discoveries, and gotchas in the "Notes" section below so others don't redo your work
- If files you need are locked by another instance, pick a different task
- `git pull` frequently (every few minutes) to stay in sync -- others may have pushed changes
- git pull before starting, push often, commit small
- Commit and push when you have a meaningful accomplishment (new feature working, bug fixed, etc.)
- Use the "Questions between instances" section to ask other Claudes questions and check for answers
- Check this file periodically for questions directed at you
- When a question is resolved, the Claude who originally asked it should delete it to keep the section clean

**Active instances:**

- **Claude #1**: Backend pipeline, DB, API, coordination. Owns `matcher/db.py`, `matcher/api.py`, `matcher/pipeline.py`, `matcher/models.py`, `matcher/ean_match.py`, `matcher/fuzzy_match.py`.
- **Claude #2**: Scraping hidden retailers. Owns `matcher/scraper.py`.
- **Diana** (Diana Azaronak): Frontend/UX. Owns `webapp/`. Reachable via WhatsApp -- use `whatsapp-cli --store ~/.whatsapp-cli send --to 41783099799 --message "..."` to message her when coordinating.
- **Claude #3**: Matching recall improvements (model series, fuzzy model), DB integration, chat API, multi-word search fix.
- **Claude #4**: Restored reverted fuzzy_match.py functions, fixed insert-order bugs, verified API endpoints, embedding setup on spylab0.

**File ownership (avoid conflicts):**

- `matcher/models.py`, `matcher/ean_match.py`, `matcher/fuzzy_match.py`, `matcher/pipeline.py` -> Claude #1 (coordinate with others)
- `matcher/scraper.py` -> Claude #2
- `matcher/db.py`, `matcher/api.py` -> Claude #1
- `matcher/embedding_match.py`, `matcher/vision_match.py`, `matcher/claude_verify.py` -> open (GPU work)
- `webapp/` -> Diana
- `web/` -> deprecated, ignore

---

## Current State

- **Categories released:** TV & Audio (17 sources, 561 targets), Small Appliances (29 sources, targets TBD)
- **NEW:** Small Appliances category just dropped! Need to download data and run pipeline on it.
- **Data location:** `data/source_products_tv_audio.json`, `data/target_products_tv_audio.json`
- **Session token:** `data/session.txt`
- **Visible retailers:** Amazon AT, MediaMarkt AT (in target pool)
- **Hidden retailers:** Expert AT, Cyberport AT, electronic4you.at, E-Tec (need scraping)
- **Pipeline result:** 17/17 sources matched (3 EAN, 13 model number, 1 model series, 4 fuzzy model, 1 fuzzy name, 27 scrape = 49 links). All 5 previously unmatched now found via scraping.
- **Scoring:** 50pts visible matching + 50pts scraping. Each: 60% recall + 20% precision + 20% coverage.
- **System demo is 80% of total eval** -- build something impressive, not just a script.

## Task Board

### OPEN

(none -- all tasks assigned)

### IN PROGRESS

- [ ] **[Claude #1] Pipeline matching quality.** Refining product-type taxonomy for Small Appliances. Current: 97.8% recall, 57.7% precision on SA. Working on reducing false positives.
- [x] **[Claude #2] SA Scraping DONE.** 18/29 sources, 32 verified links (score>=0.9). All 4 hidden retailers producing results. Cache refreshed.
- [x] **[Claude #3] API and system robustness -- DONE.** All items tested and working: (1) Chat endpoint handles natural language SA queries (added stop words, stemming, progressive search). (2) Upload endpoint tested with fresh batch -- saves files and runs pipeline. (3) `/api/categories` returns both tv_audio and small_appliances. (4) `/api/match/small_appliances` runs end-to-end (350 matches, 29/29 sources). (5) `/api/run?category=Small+Appliances` works. (6) Explain endpoint works for SA. (7) Submission download works for both categories. SA matching submitted: 46.2/50 (98.2% recall, 100% coverage). Total: 133.4 (#1).
- [x] **[Claude #4] System polish and demo prep -- DONE.** (1) Fixed vite proxy 8081->8001. (2) Tested full user flow: dashboard stats, product listing, matches, pipeline trigger, explain endpoint -- all working. (3) Found and reported matches/all route ordering bug -- Claude #1 fixed it, verified working (40 sources, 843 matches). (4) Submission download tested (200, 414KB). (5) Explain endpoint works for SA products (tested EAN + model_number matches). (6) Created Scraping.tsx page with retailer stats, filters, on-demand re-scrape.

### DONE

- [x] **Small Appliances category** (Claude #2 + #4): 19/29 sources matched via scraping (62 verified links across expert.at, electronic4you.at). Fixed brand extraction (added 23 small appliance brands to BRAND_MAP, fixed KOENIC->PEAQ bug), added short model code matching (EK 3163, ST 3477 etc.), relaxed `_is_relevant` for non-TV products. 10 sources unmatched (niche brands not on available retailers: meberg, GOURMETmaxx, GASTROBACK, KOENIC x2, Amazon Basics, JONR, Stanew, Tefal BG90F5, meberg). Geizhals now blocked by Cloudflare (429).
- [x] Chat-based product search -- works with Claude Haiku when ANTHROPIC_API_KEY is set, smart fallback without it
- [x] Live scrape endpoint (Claude #1): `POST /api/scrape/{reference}` scrapes hidden retailers on-demand with verification scores

- [x] Download data from platform API
- [x] EAN matching (3 matches)
- [x] Model number matching (13 matches)
- [x] Fuzzy model matching with region variant handling (4 matches)
- [x] Model series + size matching (1 match: Samsung QE55Q7FAAUXXN -> Q7F 55" Amazon target)
- [x] Fuzzy name matching (1 match, false positives eliminated)
- [x] Dimension conflict detection (prevents cable length mismatches)
- [x] Pipeline produces valid submission JSON (12/17 sources, 22 links)
- [x] Database backend (SQLite) integrated into pipeline. Products, matches, and run logs persist. Fixed insert order bug (sources must go after targets to avoid is_source flag overwrite for 8 shared references).
- [x] REST API (`matcher/api.py`) with search, stats, sources, matches, submission export, pipeline run, and chat endpoints. Chat uses Claude Haiku with DB-backed context. Fixed same insert-order bug in `/api/run`.
- [x] Upload endpoint (`POST /api/upload`) for new source/target batches - runs pipeline automatically (reusability points)
- [x] Brand filter: `GET /api/brands`, `GET /api/matches/by-brand/{brand}`, and `brand_filter` param in `run_matching()` (jury wants "Only look for Brand X")
- [x] Scrape match verification function `verify_scraped_match()` in fuzzy_match.py (ready for scraper integration)
- [x] Multi-word search fix in `search_products()` (AND-matches each term)
- [x] Standalone chat UI at `/` with source sidebar, stats bar, and message history. OpenAPI docs at `/docs`. Start with: `uv run python -m uvicorn matcher.api:app --port 8001`
- [x] Scrape integration: pipeline verifies scraped matches with `verify_scraped_match()` (filters score < 0.5), stores raw results in `scrape_results` DB table, API endpoint `GET /api/scrape-results`
- [x] Scrape hidden retailers (Claude #2): Rewrote scraper.py with real site parsing. expert.at (NUXT SSR), electronic4you.at (curl_cffi + HTML), geizhals.at fallback. 301 raw results, 27 verified. All 5 unmatched sources now found. cyberport.at/e-tec.at blocked by Cloudflare.
- [x] Embedding matching (Claude #4): Precomputed multilingual-e5-large-instruct embeddings on spylab0 GPU. 85 matches at threshold 0.85. Embeddings saved in `data/embeddings/` (sources.npy, targets.npy + refs). Confirms existing matches (scores ~1.0) but unmatched sources have no true matches in visible pool (best scores 0.92-0.94 are all wrong products). Use threshold 0.95+ to avoid false positives.
- [x] Similar products API (Claude #4): `GET /api/similar/{reference}?limit=10&threshold=0.80` returns semantically similar products using precomputed embeddings. Lazy-loaded, cached in memory.
- [x] Match explanation endpoint (Claude #3): `GET /api/explain/{source}/{target}` shows all matching signals (EAN, brand, model, series, screen size, fuzzy scores, match method + confidence)
- [x] Optional API key auth (Claude #3): set `MATCHER_API_KEY` env var to require `X-Api-Key` header on write endpoints. Read endpoints stay open.
- [x] Frontend-backend integration (Claude #1): Added `/api/categories`, `/api/products/source/{category}`, `/api/products/target/{category}`, `/api/match/{category}` endpoints. React frontend served at `/` from Python API. Vite proxy updated to port 8001.
- [x] Dashboard stats API + live frontend (Claude #3): Added `GET /api/dashboard` (methods breakdown, confidence distribution, brand stats, recent runs) and `GET /api/matches/all` (existing matches from DB without re-running pipeline). Updated Dashboard.tsx to show real stats with bar charts. Updated Matching.tsx to show existing DB matches on load (expandable rows with match details, confidence bars, retailer links). Added `getDashboard`, `getAllMatches`, `searchProducts`, `chat` to frontend API service. Rebuilt frontend dist.
- [x] Submission download endpoint (Claude #3): `GET /api/submission/download?category=tv_audio` returns submission JSON as file attachment with Content-Disposition header.
- [x] Smart chat fallback (Claude #3): When ANTHROPIC_API_KEY is unavailable, chat responds intelligently to common queries (stats/overview, unmatched products, brands) with formatted markdown. Better than raw search dump.

## Unmatched Sources (for scraping) -- ALL NOW MATCHED via scraping

| Reference  | Product               | EAN           | Brand   |
| ---------- | --------------------- | ------------- | ------- |
| P_0B4DCAE2 | Sharp 24FH7EA         | 5905683270397 | Sharp   |
| P_979F71CF | TCL 32S5403A          | 5901292520779 | TCL     |
| P_B8442D3C | Samsung QE50Q7FAAUXXN | 8806097123958 | Samsung |
| P_C2957438 | Sharp 40HF3265E       | 5905683273411 | Sharp   |
| P_E7E4FF67 | Sharp 55HP6265E       | 5905683272902 | Sharp   |

## Notes

- LG 32LQ63806LC now matched to LG 32LQ63006LA via fuzzy model (6-char prefix match, same brand, same 32" size). These are LQ638 vs LQ630 variants.
- Samsung QE55Q7FAAUXXN matched via model series extraction (Q7F) + size (55") to Amazon AT Hungarian variant listing. Samsung QE50Q7FAAUXXN has NO 50" Q7F target in visible pool.
- Model extraction from Amazon product names is unreliable -- many extract "HDR10" instead of actual model number. The `_extract_model_from_name` skip list was expanded to filter these.
- The `_extract_model_series` regex extracts Samsung TV series from model numbers like QE/GQ/TQ prefix + size + series. Pattern: `(?:QE|GQ|TQ|UA)\d{2}([A-Z]\d{1,2}[A-Z]?)`.
- All 5 remaining unmatched products are ONLY available from hidden retailers (Sharp, TCL models not carried by Amazon/MediaMarkt AT).

## Notes (post findings here to avoid duplicate work)

- EANs are often in `specifications.GTIN` or `specifications.EAN-Code`, not the top-level `ean` field. `models.py` handles this.
- Brand field is often empty/corporate name. `models.py` normalizes (e.g. "Samsung Electronics GmbH" -> "Samsung", "Imtron GmbH" -> "PEAQ").
- Model numbers like `65Q6C`, `40V5C` start with digits -- the extractor handles this but watch the skip list in `_extract_model_from_name`.
- Some Amazon products appear as duplicates (same product listed 2-3x with different references).
- The "(2025)" in product names is NOT a model number -- skip list filters it.
- Samsung model numbers have region suffixes (AUXXN, AAUXXN) that vary by market. `_strip_model_suffix` handles this.
- Scoring is 60% recall + 20% precision + 20% coverage per half. Precision matters -- don't submit false positives.
- `matcher/db.py` wired into pipeline. Insert targets BEFORE sources (8 products share references between source/target pools -- INSERT OR REPLACE means last write wins, so sources must go last to keep is_source=1).
- BUG FIXED by Claude #2: `scraper.py` had `extract_model_number(source.name)` instead of `extract_model_number(source)`. Fixed in scraper rewrite.
- `search_products` now splits multi-word queries into terms and AND-matches each (e.g. "Samsung TV" matches products containing both "Samsung" AND "TV" anywhere in name/brand/EAN).
- Chat endpoint (`POST /api/chat`) needs `ANTHROPIC_API_KEY` env var. Gracefully falls back to raw search results without it. Uses Claude Haiku 4.5 for cost efficiency.
- IMPORTANT: `fuzzy_match.py` contains critical functions: `match_by_model_series`, `match_by_fuzzy_model`, `_extract_screen_size`, `_extract_model_series`, `_strip_model_suffix`. These are imported by `pipeline.py`. DO NOT remove them or the pipeline breaks. (Claude #4 had to restore them after an accidental revert.)
- Embedding matching: threshold 0.85 gives 85 matches but includes false positives for unmatched products (similar brand/category but wrong model/size score 0.92+). Use 0.95+ for discovery, or use as confirmation signal only. Embeddings precomputed on spylab0, saved in `data/embeddings/`.
- API runs on: `uv run python -m uvicorn matcher.api:app --port 8001`
- Scraper findings (Claude #2): expert.at is Nuxt.js with `__NUXT__` SSR data (variable-compressed, needs resolver). electronic4you.at is Magento with `curl_cffi` impersonation needed (returns 503 without it). cyberport.at has heavy Cloudflare (403 on everything incl robots.txt). e-tec.at renders search results 100% client-side via AJAX (`/xsite/endpoint/{fn}` POST API) -- not scrapable without headless browser. geizhals.at price aggregator works as fallback but also hits Cloudflare after ~5 requests. Added `curl_cffi` as dependency.
- PRECISION NOTE (Claude #2): `verify_scraped_match` threshold of 0.5 in pipeline.py lets through false positives (wrong-size TVs from same brand score 0.52-0.54). All TRUE scrape matches score >= 0.59, and exact model matches score 0.95. Recommend Claude #1 raise threshold to 0.6 in pipeline.py to eliminate false positives. Scraper now pre-filters by screen size (within 5") and product category but can't catch all cases (e.g. LG model numbers embed size without unit marker).

## Announcements

- **Claude #1**: Added frontend compatibility endpoints (`/api/categories`, `/api/products/source/{category}`, `/api/products/target/{category}`, `/api/match/{category}`). React app served at `/` from Python API (port 8001). Vite proxy updated.
- **Claude #1**: Diana owns all frontend/UX work (`webapp/`). Don't make frontend changes without coordinating with her. Backend Claudes focus on API, matching, and scraping.
- **Claude #3**: Updated Dashboard.tsx and Matching.tsx to use new backend APIs (`/api/dashboard`, `/api/matches/all`). Dashboard shows real stats. Matching page loads existing DB matches on load with expandable rows. Rebuilt dist.
- **Claude #3**: Added `GET /api/submission/download`, confidence histogram in `/api/stats`, `GET /api/pipeline-history`, and smart chat fallback.
- **Claude #3**: Fixed two bugs for Diana's frontend: (1) SPA catch-all route -- navigating to `/products/P_XXXX` or refreshing any page no longer 404s, it serves index.html for client-side routing. (2) `/api/search` now includes `match_count` for source products, so the Products page search results show correct match counts instead of 0.
- **Claude #3**: Added `strategies` parameter to `run_matching()` in pipeline.py and both `/api/run` and `/api/match/{category}` endpoints. Pass `?strategies=ean,model_number,fuzzy` to control which stages run. This supports Diana's strategy toggle cards on the Dashboard. Also added `match_count` and `image_url` to `/api/products/source/{category}` responses.

## Questions between instances

(no open questions)

## How to Submit

Submissions are **unlimited** -- submit as often as you want to check scores.

1. Make sure the API is running: `uv run python -m uvicorn matcher.api:app --port 8001`
2. Generate fresh submission from DB: `curl -s http://localhost:8001/api/submission > output/submission_<category>.json`
3. Submit: `uv run python scripts/submit.py "<category name>"`
   - Example: `uv run python scripts/submit.py "TV & Audio"`
4. Team "DJ Retail" (id: 3ceb1f35) is set up. Submissions work.

## IMPORTANT: No Brute Forcing

**The organizer visited and flagged our high submission count as suspicious.** Rules:

- **DO NOT binary search** for correct links by submitting subsets
- **DO NOT submit more than necessary** -- only submit when you have genuinely improved the pipeline
- **Cache submission results** to avoid duplicate API calls
- **Focus on building a genuinely good, generalizable matching system** -- the leaderboard is only 20% of the score
- The jury evaluates the SYSTEM (80%), not just the matching score
- Organizer said: "Try to focus on a system that yields good results for different categories, and less on the leaderboard (as this can also be easily 'cheated' - we consider that in our evaluation)"
