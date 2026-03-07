# Coordination Board

Shared board for all Claude instances on this project. READ THIS FIRST before doing any work.

**Protocol:**

- Read this file before starting work
- Claim a task by writing your session info next to it
- Update status when done -- move task to DONE with a summary of what changed
- Post findings, discoveries, and gotchas in the "Notes" section below so others don't redo your work
- If files you need are locked by another instance, pick a different task
- git pull before starting, push often, commit small
- Commit and push when you have a meaningful accomplishment (new feature working, bug fixed, etc.)

**Active instances:**

- **Claude #1 (Claude-Main)**: Backend pipeline, DB, API, coordination. Owns `matcher/db.py`, `matcher/api.py`, `matcher/pipeline.py`, `matcher/models.py`, `matcher/ean_match.py`, `matcher/fuzzy_match.py`.
- **Claude-Scraper**: Scraping hidden retailers. Owns `matcher/scraper.py`.
- **Claude-Matching**: Improving matching strategies. Can edit `matcher/fuzzy_match.py` (coordinate with Claude-Main).
- **Diana**: Frontend/UX. Owns `webapp/`.
- **Claude-3**: Matching recall improvements (model series, fuzzy model), DB integration, chat API, multi-word search fix.
- **Claude-4**: Restored reverted fuzzy_match.py functions, fixed insert-order bugs, verified API endpoints, coordination. Active now.

**File ownership (avoid conflicts):**

- `matcher/models.py`, `matcher/ean_match.py`, `matcher/fuzzy_match.py`, `matcher/pipeline.py` -> Claude-Main + Claude-Matching (coordinate)
- `matcher/scraper.py` -> Claude-Scraper
- `matcher/db.py`, `matcher/api.py` -> Claude-Main
- `matcher/embedding_match.py`, `matcher/vision_match.py`, `matcher/claude_verify.py` -> open (GPU work)
- `webapp/` -> Diana
- `web/` -> deprecated, ignore

---

## Current State

- **Category released:** TV & Audio (17 sources, 561 targets)
- **Data location:** `data/source_products_tv_audio.json`, `data/target_products_tv_audio.json`
- **Session token:** `data/session.txt`
- **Visible retailers:** Amazon AT, MediaMarkt AT (in target pool)
- **Hidden retailers:** Expert AT, Cyberport AT, electronic4you.at, E-Tec (need scraping)
- **Pipeline result:** 12/17 sources matched (3 EAN, 13 model number, 1 model series, 4 fuzzy model, 1 fuzzy name = 22 links). 5 unmatched have NO targets in visible pool -- only findable via scraping.
- **Scoring:** 50pts visible matching + 50pts scraping. Each: 60% recall + 20% precision + 20% coverage.
- **System demo is 80% of total eval** -- build something impressive, not just a script.

## Task Board

### OPEN

- [ ] Integrate scraped results into pipeline output
- [ ] Set up embedding matching on spylab0 (GPU needed) -> Claude-4

### IN PROGRESS

- [x] Scrape hidden retailers (expert.at, cyberport.at, electronic4you.at, e-tec.at) -> SCRAPER
- [ ] Chat-based product search interface -> Claude-3 (API done, needs ANTHROPIC_API_KEY to work with Claude Haiku; fallback mode returns raw search results)

### DONE

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

## Unmatched Sources (for scraping)

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
- BUG in `scraper.py:261`: `extract_model_number(source.name)` should be `extract_model_number(source)` -- function takes a Product, not a string. SCRAPER instance please fix.
- `search_products` now splits multi-word queries into terms and AND-matches each (e.g. "Samsung TV" matches products containing both "Samsung" AND "TV" anywhere in name/brand/EAN).
- Chat endpoint (`POST /api/chat`) needs `ANTHROPIC_API_KEY` env var. Gracefully falls back to raw search results without it. Uses Claude Haiku 4.5 for cost efficiency.
- IMPORTANT: `fuzzy_match.py` contains critical functions: `match_by_model_series`, `match_by_fuzzy_model`, `_extract_screen_size`, `_extract_model_series`, `_strip_model_suffix`. These are imported by `pipeline.py`. DO NOT remove them or the pipeline breaks. (Claude-4 had to restore them after an accidental revert.)
- API runs on: `uv run python -m uvicorn matcher.api:app --port 8001`
