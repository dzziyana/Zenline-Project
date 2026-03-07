"""REST API for the product matcher.

Provides endpoints for searching products, viewing matches,
running the pipeline, chat-based search, and exporting submissions.
"""

from __future__ import annotations

import json
from pathlib import Path

import os

from fastapi import Depends, FastAPI, File, Header, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .db import (
    get_connection,
    get_all_sources,
    get_matches_for_source,
    get_product,
    get_stats,
    get_unmatched_sources,
    init_db,
    search_products,
)

app = FastAPI(title="Product Matcher API", version="0.1.0", docs_url="/docs")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


API_KEY = os.environ.get("MATCHER_API_KEY")


def _check_auth(x_api_key: str | None = Header(None)):
    """Optional API key auth. If MATCHER_API_KEY is set, all write endpoints require it."""
    if API_KEY and x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


def _get_db():
    conn = get_connection()
    init_db(conn)
    return conn


_WEBAPP_DIST = Path(__file__).parent.parent / "webapp" / "frontend" / "dist"


@app.get("/chat", response_class=HTMLResponse)
def chat_ui():
    """Serve the product matcher chat UI."""
    return _CHAT_HTML


@app.get("/", response_class=HTMLResponse)
def ui():
    """Serve the React frontend if built, otherwise the chat UI."""
    index = _WEBAPP_DIST / "index.html"
    if index.exists():
        return index.read_text()
    return _CHAT_HTML


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/stats")
def stats():
    conn = _get_db()
    try:
        return get_stats(conn)
    finally:
        conn.close()


@app.get("/api/sources")
def list_sources():
    conn = _get_db()
    try:
        sources = get_all_sources(conn)
        # Attach match count per source
        for s in sources:
            matches = get_matches_for_source(conn, s["reference"])
            s["match_count"] = len(matches)
            s["specifications"] = json.loads(s.get("specifications", "{}"))
        return {"sources": sources, "total": len(sources)}
    finally:
        conn.close()


@app.get("/api/sources/unmatched")
def list_unmatched():
    conn = _get_db()
    try:
        unmatched = get_unmatched_sources(conn)
        for s in unmatched:
            s["specifications"] = json.loads(s.get("specifications", "{}"))
        return {"sources": unmatched, "total": len(unmatched)}
    finally:
        conn.close()


@app.get("/api/products/{reference}")
def product_detail(reference: str):
    conn = _get_db()
    try:
        product = get_product(conn, reference)
        matches = get_matches_for_source(conn, reference) if product else []
        if not product:
            # Fallback: search JSON data files
            from .models import Product
            data_dir = Path("data")
            for f in data_dir.glob("*_products_*.json"):
                with open(f) as fh:
                    data = json.load(fh)
                for d in data:
                    if d.get("reference") == reference:
                        p = Product.from_dict(d)
                        product = {
                            "reference": p.reference,
                            "name": p.name,
                            "brand": p.brand,
                            "ean": p.ean,
                            "category": p.category,
                            "price": p.price_eur,
                            "price_eur": p.price_eur,
                            "image_url": d.get("image_url"),
                            "url": d.get("url"),
                            "retailer": d.get("retailer"),
                            "specifications": d.get("specifications", {}),
                        }
                        break
                if product:
                    break
        if not product:
            return JSONResponse(status_code=404, content={"error": "Product not found"})
        return {"product": product, "matches": matches}
    finally:
        conn.close()


@app.get("/api/explain/{source_ref}/{target_ref}")
def explain_match(source_ref: str, target_ref: str):
    """Explain why two products were matched (or not)."""
    from .fuzzy_match import (
        extract_model_number, normalize_name, _extract_screen_size,
        _extract_model_series, _strip_model_suffix, verify_scraped_match,
    )
    from .ean_match import _get_eans
    from rapidfuzz import fuzz

    conn = _get_db()
    try:
        source = get_product(conn, source_ref)
        target = get_product(conn, target_ref)
        if not source or not target:
            return JSONResponse(status_code=404, content={"error": "Product not found"})

        from .models import Product
        src = Product.from_dict(source)
        tgt = Product.from_dict(target)

        src_eans = _get_eans(src)
        tgt_eans = _get_eans(tgt)
        src_model = extract_model_number(src)
        tgt_model = extract_model_number(tgt)
        src_name = normalize_name(src.name)
        tgt_name = normalize_name(tgt.name)

        explanation = {
            "source": {"ref": source_ref, "name": src.name, "brand": src.brand, "model": src_model, "eans": src_eans},
            "target": {"ref": target_ref, "name": tgt.name, "brand": tgt.brand, "model": tgt_model, "eans": tgt_eans},
            "signals": {},
        }

        # EAN match
        ean_overlap = set(src_eans) & set(tgt_eans)
        explanation["signals"]["ean_match"] = bool(ean_overlap)
        if ean_overlap:
            explanation["signals"]["ean_shared"] = list(ean_overlap)

        # Brand match
        explanation["signals"]["brand_match"] = (
            bool(src.brand and tgt.brand) and src.brand.lower() == tgt.brand.lower()
        )

        # Model number
        explanation["signals"]["model_exact"] = bool(src_model and tgt_model and src_model == tgt_model)
        if src_model and tgt_model:
            src_stripped = _strip_model_suffix(src_model)
            tgt_stripped = _strip_model_suffix(tgt_model)
            prefix_len = sum(1 for a, b in zip(src_stripped, tgt_stripped) if a == b)
            explanation["signals"]["model_prefix_match"] = prefix_len

        # Series
        src_series = _extract_model_series(src_model) if src_model else None
        tgt_series = _extract_model_series(tgt_model) if tgt_model else None
        explanation["signals"]["series_match"] = bool(src_series and tgt_series and src_series == tgt_series)

        # Screen size
        src_size = _extract_screen_size(src.name)
        tgt_size = _extract_screen_size(tgt.name)
        explanation["signals"]["screen_size"] = {"source": src_size, "target": tgt_size, "match": src_size == tgt_size if src_size and tgt_size else None}

        # Fuzzy scores
        explanation["signals"]["fuzzy_token_sort"] = round(fuzz.token_sort_ratio(src_name, tgt_name), 1)
        explanation["signals"]["fuzzy_token_set"] = round(fuzz.token_set_ratio(src_name, tgt_name), 1)

        # Check existing match
        match_row = conn.execute(
            "SELECT * FROM matches WHERE source_reference = ? AND target_reference = ?",
            (source_ref, target_ref)
        ).fetchone()
        if match_row:
            explanation["matched"] = True
            explanation["method"] = match_row["method"]
            explanation["confidence"] = match_row["confidence"]
        else:
            explanation["matched"] = False

        return explanation
    finally:
        conn.close()


@app.get("/api/search")
def search(
    q: str = Query(..., min_length=1, description="Search query"),
    brand: str | None = Query(None),
    retailer: str | None = Query(None),
    source_only: bool = Query(False),
    limit: int = Query(20, le=100),
):
    conn = _get_db()
    try:
        results = search_products(conn, q, limit=limit, brand=brand,
                                  retailer=retailer, source_only=source_only)
        for r in results:
            r["specifications"] = json.loads(r.get("specifications", "{}"))
            if r.get("is_source"):
                matches = get_matches_for_source(conn, r["reference"])
                r["match_count"] = len(matches)
        return {"results": results, "total": len(results), "query": q}
    finally:
        conn.close()


@app.get("/api/matches/all")
def get_all_matches():
    """Return all existing matches from DB without re-running the pipeline."""
    conn = _get_db()
    try:
        sources = get_all_sources(conn)
        result = []
        for s in sources:
            matches = get_matches_for_source(conn, s["reference"])
            s["specifications"] = json.loads(s.get("specifications", "{}"))
            result.append({
                "source": s,
                "matches": matches,
            })
        return {
            "total_sources": len(sources),
            "total_matched": sum(1 for r in result if r["matches"]),
            "total_matches": sum(len(r["matches"]) for r in result),
            "results": result,
        }
    finally:
        conn.close()


@app.get("/api/matches/{source_reference}")
def get_matches(source_reference: str):
    conn = _get_db()
    try:
        matches = get_matches_for_source(conn, source_reference)
        source = get_product(conn, source_reference)
        return {"source": source, "matches": matches, "total": len(matches)}
    finally:
        conn.close()


def _build_submission(conn, category: str | None = None) -> list[dict]:
    """Build submission JSON from current DB matches, optionally filtered by category."""
    if category:
        # Load source references for this category from data files
        data_dir = Path("data")
        path = data_dir / f"source_products_{category}.json"
        if path.exists():
            with open(path) as f:
                cat_sources = json.load(f)
            source_refs = {s["reference"] for s in cat_sources}
        else:
            source_refs = None
    else:
        source_refs = None

    sources = get_all_sources(conn)
    submission = []
    for s in sources:
        if source_refs is not None and s["reference"] not in source_refs:
            continue
        matches = get_matches_for_source(conn, s["reference"])
        if matches:
            submission.append({
                "source_reference": s["reference"],
                "competitors": [
                    {
                        "reference": m["target_reference"],
                        "competitor_retailer": m["target_retailer"],
                        "competitor_product_name": m["target_name"],
                        "competitor_url": m["target_url"],
                        "competitor_price": m["target_price"],
                    }
                    for m in matches
                ]
            })
    return submission


@app.get("/api/submission")
def get_submission(category: str | None = Query(None, description="Category slug (e.g. tv_audio, small_appliances)")):
    """Export current matches as submission JSON, optionally filtered by category."""
    conn = _get_db()
    try:
        return _build_submission(conn, category)
    finally:
        conn.close()


@app.get("/api/submission/download")
def download_submission(category: str = Query("tv_audio")):
    """Download submission as a JSON file attachment."""
    from fastapi.responses import Response

    conn = _get_db()
    try:
        submission = _build_submission(conn, category)
    finally:
        conn.close()

    content = json.dumps(submission, indent=2)
    filename = f"submission_{category}.json"
    return Response(
        content=content,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.post("/api/run", dependencies=[Depends(_check_auth)])
def run_pipeline_endpoint(
    category: str = Query("TV & Audio"),
    scrape: bool = Query(False),
    strategies: str | None = Query(None, description="Comma-separated strategy IDs (e.g. ean,model_number,fuzzy,scrape)"),
):
    """Trigger a pipeline run. Requires API key if MATCHER_API_KEY is set."""
    from .pipeline import load_products, run_matching, dedupe_matches
    from .db import insert_products, insert_matches, log_pipeline_run

    data_dir = Path("data")
    safe_name = category.lower().replace(" & ", "_").replace(" ", "_")
    source_path = data_dir / f"source_products_{safe_name}.json"
    target_path = data_dir / f"target_products_{safe_name}.json"

    if not source_path.exists() or not target_path.exists():
        return JSONResponse(status_code=404, content={"error": f"Data not found for category: {category}"})

    strategy_set = set(strategies.split(",")) if strategies else None
    sources = load_products(source_path)
    targets = load_products(target_path)
    matches = run_matching(sources, targets, do_scrape=scrape, strategies=strategy_set)

    conn = _get_db()
    try:
        insert_products(conn, targets, is_source=False)
        insert_products(conn, sources, is_source=True)
        insert_matches(conn, matches)
        log_pipeline_run(conn, category, len(sources), len(targets), matches)
    finally:
        conn.close()

    matched_sources = len({m.source_reference for m in matches})
    return {
        "status": "complete",
        "category": category,
        "sources": len(sources),
        "targets": len(targets),
        "matches": len(matches),
        "sources_matched": matched_sources,
    }


class ChatRequest(BaseModel):
    message: str
    history: list[dict] = []


CHAT_SYSTEM_PROMPT = """You are a product matching assistant for an Austrian electronics retail comparison tool.
You help users search for products, find matches, and understand matching results.

You have access to a database of source products (the products we want to find matches for) and target products (from competitor retailers like Amazon AT and MediaMarkt AT).

When the user asks about products, you receive search results as context. Use them to answer.
Be concise and format product info clearly. Use markdown for formatting.

Available data:
- Categories: TV & Audio, Small Appliances
- TV brands: Samsung, LG, Sharp, TCL, CHIQ, PEAQ, Xiaomi, Sony, Philips, Hisense, Sonos, JBL, Bose
- Appliance brands: Tefal, Beurer, WMF, Braun, Oral-B, Clatronic, SEVERIN, Rommelsbacher, SILVA, Kenwood, REMINGTON, KOENIC, GASTROBACK, JONR, Mova
- Retailers: Amazon AT, MediaMarkt AT (visible); Expert AT, electronic4you.at, Cyberport AT, E-Tec AT (scraped)

Respond in the same language the user writes in (German or English)."""


_STOP_WORDS = {"find", "show", "search", "list", "get", "me", "all", "the", "a",
                "an", "in", "for", "of", "with", "and", "or", "is", "are", "my",
                "what", "which", "where", "how", "can", "do", "does", "please",
                "i", "want", "need", "looking", "any", "some", "about",
                "small", "appliances", "appliance", "products", "product",
                "category", "categories", "audio", "tv"}


def _stem_word(word: str) -> str:
    """Basic stemming: strip common English/German suffixes for search."""
    w = word.lower()
    for suffix in ["ers", "ies", "es", "en", "er", "s"]:
        if w.endswith(suffix) and len(w) > len(suffix) + 2:
            return w[:-len(suffix)]
    return w


def _chat_search(query: str) -> str:
    """Search the DB and format results for the chat context."""
    # Strip stop words and stem remaining words
    words = query.split()
    filtered = [_stem_word(w) for w in words if w.lower() not in _STOP_WORDS]
    search_query = " ".join(filtered) if filtered else query

    conn = _get_db()
    try:
        # Try full query, then progressively fewer terms until we find results
        search_words = search_query.split()
        results = search_products(conn, search_query, limit=10)
        if not results and len(search_words) > 1:
            for n in range(len(search_words) - 1, 0, -1):
                results = search_products(conn, " ".join(search_words[:n]), limit=10)
                if results:
                    break
        if not results:
            return f"No products found for '{query}'."

        lines = []
        for r in results:
            source_tag = " [SOURCE]" if r.get("is_source") else ""
            price = f" - EUR {r['price_eur']:.2f}" if r.get("price_eur") else ""
            lines.append(f"- {r['name']}{price} ({r['retailer'] or 'unknown'}){source_tag} [ref: {r['reference']}]")

            if r.get("is_source"):
                matches = get_matches_for_source(conn, r["reference"])
                if matches:
                    for m in matches[:3]:
                        lines.append(f"  -> Match: {m['target_name'][:60]} ({m['target_retailer']}, method={m['method']}, confidence={m['confidence']:.2f})")
                else:
                    lines.append("  -> No matches found yet")
        return "\n".join(lines)
    finally:
        conn.close()


_trends_cache: dict = {}
_trends_cache_time: float = 0

@app.get("/api/trends")
def get_trends(refresh: bool = Query(False)):
    """Get trending products from tech journals and social media."""
    global _trends_cache, _trends_cache_time
    import time as _time

    # Cache for 10 minutes unless refresh requested
    if not refresh and _trends_cache and (_time.time() - _trends_cache_time) < 600:
        return _trends_cache

    from .trends import scrape_trends

    # Get known brands from data files
    brands = set()
    data_dir = Path("data")
    for f in data_dir.glob("source_products_*.json"):
        with open(f) as fh:
            for p in json.load(fh):
                if p.get("brand"):
                    brands.add(p["brand"])

    result = scrape_trends(sorted(brands) if brands else None)
    _trends_cache = result
    _trends_cache_time = _time.time()
    return result


@app.post("/api/chat")
def chat(req: ChatRequest):
    """Chat-based product search using Claude Haiku."""
    conn = _get_db()
    try:
        stats = get_stats(conn)
    finally:
        conn.close()

    context = f"Database: {stats['source_count']} sources, {stats['target_count']} targets, {stats['match_count']} matches ({stats['sources_matched']} sources matched)."

    search_context = _chat_search(req.message)

    messages = []
    for h in req.history[-10:]:
        messages.append({"role": h["role"], "content": h["content"]})

    messages.append({
        "role": "user",
        "content": f"{req.message}\n\n[Search results]\n{search_context}\n\n[Stats]\n{context}",
    })

    try:
        import anthropic
        client = anthropic.Anthropic()
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            system=CHAT_SYSTEM_PROMPT,
            messages=messages,
        )
        reply = response.content[0].text
    except Exception:
        reply = _format_smart_fallback(req.message, search_context, stats)

    return {"reply": reply, "search_results": search_context}


def _format_smart_fallback(query: str, search_context: str, stats: dict) -> str:
    """Format a helpful response when Claude API is unavailable."""
    q = query.lower().strip()

    # Handle common question patterns
    if any(w in q for w in ["stat", "overview", "how many", "summary"]):
        methods = stats.get("methods", {})
        method_str = ", ".join(f"{k}: {v}" for k, v in methods.items()) if methods else "none yet"
        return (
            f"**Matching Overview**\n\n"
            f"- Sources: {stats['source_count']}\n"
            f"- Targets: {stats['target_count']}\n"
            f"- Matches found: {stats['match_count']}\n"
            f"- Sources matched: {stats['sources_matched']}/{stats['source_count']}\n"
            f"- Methods: {method_str}\n"
            f"- Retailers: {', '.join(stats.get('retailers', []))}"
        )

    if any(w in q for w in ["unmatched", "missing", "not found", "no match"]):
        conn = _get_db()
        try:
            unmatched = get_unmatched_sources(conn)
            if not unmatched:
                return "All source products have been matched!"
            lines = ["**Unmatched Source Products:**\n"]
            for u in unmatched:
                lines.append(f"- {u['name']} ({u['brand'] or 'unknown brand'}) [ref: {u['reference']}]")
            return "\n".join(lines)
        finally:
            conn.close()

    if any(w in q for w in ["brand", "brands"]):
        conn = _get_db()
        try:
            rows = conn.execute(
                "SELECT brand, COUNT(*) as cnt FROM products WHERE brand != '' AND is_source = 1 GROUP BY brand ORDER BY cnt DESC"
            ).fetchall()
            lines = ["**Source Product Brands:**\n"]
            for r in rows:
                lines.append(f"- {r['brand']}: {r['cnt']} products")
            return "\n".join(lines)
        finally:
            conn.close()

    # Strategy/method questions
    if any(w in q for w in ["strategy", "strategies", "method", "methods", "how did", "how was", "why matched", "why was"]):
        conn = _get_db()
        try:
            method_counts = conn.execute(
                "SELECT method, COUNT(*) as cnt FROM matches GROUP BY method ORDER BY cnt DESC"
            ).fetchall()
            if method_counts:
                lines = ["**Matching Strategies Used:**\n"]
                method_descriptions = {
                    "ean": "EAN/GTIN barcode exact match (highest confidence)",
                    "model_number": "Extracted model numbers compared within same brand",
                    "model_series": "Samsung/LG series code + screen size matching",
                    "product_line": "Same product line across different sizes",
                    "product_type": "Same product category (e.g. all toasters, all vacuums)",
                    "fuzzy_model": "Fuzzy model number matching with region variant handling",
                    "fuzzy_name": "Fuzzy product name similarity (token sort ratio)",
                    "screen_size": "Cross-brand screen size matching for TVs",
                    "scrape": "Web scraping from hidden retailers (Expert, electronic4you)",
                    "embedding": "Semantic similarity via sentence embeddings",
                }
                for r in method_counts:
                    desc = method_descriptions.get(r["method"], r["method"])
                    lines.append(f"- **{r['method']}** ({r['cnt']} matches): {desc}")

                # If the query mentions a specific product, show its match method
                search_results = search_products(conn, q, limit=3)
                for sr in search_results:
                    if sr.get("is_source"):
                        matches = get_matches_for_source(conn, sr["reference"])
                        if matches:
                            lines.append(f"\n**{sr['name']}** was matched using:")
                            for m in matches[:5]:
                                lines.append(f"  - {m['target_name'][:50]} via **{m['method']}** (confidence: {m['confidence']:.2f})")
                return "\n".join(lines)
        finally:
            conn.close()

    # Default: format search results nicely
    if "No products found" in search_context:
        return f"I couldn't find any products matching \"{query}\". Try searching by brand name, model number, or EAN."

    return f"**Search results for \"{query}\":**\n\n{search_context}"


@app.post("/api/upload", dependencies=[Depends(_check_auth)])
async def upload_data(
    sources: UploadFile = File(...),
    targets: UploadFile = File(...),
    category: str = Query("uploaded"),
):
    """Upload new source/target JSON and run pipeline. Requires API key if MATCHER_API_KEY is set."""
    from .pipeline import load_products, run_matching
    from .db import insert_products, insert_matches, log_pipeline_run
    from .models import Product

    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)

    safe_name = category.lower().replace(" & ", "_").replace(" ", "_")
    src_path = data_dir / f"source_products_{safe_name}.json"
    tgt_path = data_dir / f"target_products_{safe_name}.json"

    src_content = await sources.read()
    tgt_content = await targets.read()

    src_path.write_bytes(src_content)
    tgt_path.write_bytes(tgt_content)

    source_list = [Product.from_dict(d) for d in json.loads(src_content)]
    target_list = [Product.from_dict(d) for d in json.loads(tgt_content)]
    matches = run_matching(source_list, target_list, do_scrape=False)

    conn = _get_db()
    try:
        insert_products(conn, target_list, is_source=False)
        insert_products(conn, source_list, is_source=True)
        insert_matches(conn, matches)
        log_pipeline_run(conn, category, len(source_list), len(target_list), matches)
    finally:
        conn.close()

    matched_sources = len({m.source_reference for m in matches})
    return {
        "status": "complete",
        "category": category,
        "sources": len(source_list),
        "targets": len(target_list),
        "matches": len(matches),
        "sources_matched": matched_sources,
        "files_saved": [str(src_path), str(tgt_path)],
    }


@app.get("/api/brands")
def list_brands():
    """List all brands in the database."""
    conn = _get_db()
    try:
        rows = conn.execute(
            "SELECT brand, COUNT(*) as cnt, SUM(is_source) as source_cnt "
            "FROM products WHERE brand != '' GROUP BY brand ORDER BY cnt DESC"
        ).fetchall()
        return {
            "brands": [
                {"brand": r["brand"], "product_count": r["cnt"], "source_count": r["source_cnt"]}
                for r in rows
            ]
        }
    finally:
        conn.close()


@app.get("/api/matches/by-brand/{brand}")
def matches_by_brand(brand: str):
    """Get all matches for sources of a specific brand."""
    conn = _get_db()
    try:
        sources = conn.execute(
            "SELECT * FROM products WHERE is_source = 1 AND brand LIKE ?",
            (f"%{brand}%",)
        ).fetchall()
        result = []
        for s in sources:
            matches = get_matches_for_source(conn, s["reference"])
            result.append({
                "source": dict(s),
                "matches": matches,
                "match_count": len(matches),
            })
        return {"brand": brand, "sources": result, "total_sources": len(result)}
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Compatibility endpoints for Diana's React frontend (webapp/frontend)
# ---------------------------------------------------------------------------

@app.get("/api/categories")
def list_categories():
    """List available categories (derived from data files)."""
    data_dir = Path("data")
    categories = set()
    for f in data_dir.glob("source_products_*.json"):
        # source_products_tv_audio.json -> "tv_audio"
        name = f.stem.replace("source_products_", "")
        categories.add(name)
    return {"categories": sorted(categories)}


@app.get("/api/products/source/{category}")
def get_source_products(category: str):
    """Get source products for a category (for Diana's frontend)."""
    from .models import Product
    data_dir = Path("data")
    path = data_dir / f"source_products_{category}.json"
    if not path.exists():
        return JSONResponse(status_code=404, content={"error": f"No source data for category: {category}"})
    with open(path) as f:
        data = json.load(f)
    conn = _get_db()
    try:
        products = []
        for d in data:
            p = Product.from_dict(d)
            # Get match count from DB
            matches = get_matches_for_source(conn, p.reference)
            # Try to get image_url from DB if not in JSON
            db_product = get_product(conn, p.reference)
            image_url = d.get("image_url") or (db_product.get("image_url") if db_product else None)
            products.append({
                "reference": p.reference,
                "name": p.name,
                "brand": p.brand,
                "ean": p.ean,
                "category": p.category,
                "price": p.price_eur,
                "price_eur": p.price_eur,
                "image_url": image_url,
                "url": d.get("url"),
                "retailer": d.get("retailer"),
                "specifications": d.get("specifications", {}),
                "match_count": len(matches),
                "is_source": 1,
            })
        return {"products": products}
    finally:
        conn.close()


@app.get("/api/products/target/{category}")
def get_target_products(category: str):
    """Get target products for a category (for Diana's frontend)."""
    from .models import Product
    data_dir = Path("data")
    path = data_dir / f"target_products_{category}.json"
    if not path.exists():
        return JSONResponse(status_code=404, content={"error": f"No target data for category: {category}"})
    with open(path) as f:
        data = json.load(f)
    products = []
    for d in data:
        p = Product.from_dict(d)
        products.append({
            "reference": p.reference,
            "name": p.name,
            "brand": p.brand,
            "ean": p.ean,
            "retailer": p.retailer,
            "url": p.url,
            "price": p.price_eur,
            "category": p.category,
        })
    return {"products": products}


@app.post("/api/match/{category}")
def run_match_for_category(
    category: str,
    useLlm: bool = Query(False),
    fuzzyThreshold: float = Query(75.0),
    strategies: str | None = Query(None, description="Comma-separated strategy IDs"),
):
    """Run matching for a category and return results in frontend format."""
    from .pipeline import load_products, run_matching
    from .db import insert_products, insert_matches, log_pipeline_run

    data_dir = Path("data")
    source_path = data_dir / f"source_products_{category}.json"
    target_path = data_dir / f"target_products_{category}.json"

    if not source_path.exists() or not target_path.exists():
        return JSONResponse(status_code=404, content={"error": f"Data not found for category: {category}"})

    strategy_set = set(strategies.split(",")) if strategies else None
    do_scrape = "scrape" in strategy_set if strategy_set else False
    sources = load_products(source_path)
    targets = load_products(target_path)
    matches = run_matching(sources, targets, do_scrape=do_scrape, strategies=strategy_set)

    conn = _get_db()
    try:
        insert_products(conn, targets, is_source=False)
        insert_products(conn, sources, is_source=True)
        insert_matches(conn, matches)
        log_pipeline_run(conn, category, len(sources), len(targets), matches)
    finally:
        conn.close()

    # Build submission format with confidence and match_method for frontend
    by_source: dict[str, list] = {}
    for m in matches:
        by_source.setdefault(m.source_reference, []).append({
            "reference": m.target_reference,
            "competitor_retailer": m.target_retailer,
            "competitor_product_name": m.target_name,
            "competitor_url": m.target_url,
            "competitor_price": m.target_price,
            "confidence": m.confidence,
            "match_method": m.method,
        })

    submissions = []
    for s in sources:
        submissions.append({
            "source_reference": s.reference,
            "competitors": by_source.get(s.reference, []),
        })

    return {
        "category": category,
        "total_sources": len(sources),
        "total_matches": len(matches),
        "submissions": submissions,
    }


@app.get("/api/dashboard")
def dashboard():
    """Comprehensive dashboard stats in a single call (for frontend)."""
    conn = _get_db()
    try:
        stats = get_stats(conn)

        # Methods breakdown with friendly names
        method_labels = {
            "ean": "EAN Exact",
            "model_number": "Model Number",
            "model_series": "Model Series",
            "fuzzy_model": "Fuzzy Model",
            "fuzzy_name": "Fuzzy Name",
            "scrape": "Web Scraping",
            "embedding": "Embedding",
        }
        methods = [
            {"method": k, "label": method_labels.get(k, k), "count": v}
            for k, v in stats.get("methods", {}).items()
        ]

        # Top brands by match count
        brand_rows = conn.execute("""
            SELECT p.brand, COUNT(DISTINCT m.source_reference) as matched_sources,
                   COUNT(m.id) as total_matches
            FROM products p
            JOIN matches m ON p.reference = m.source_reference
            WHERE p.is_source = 1 AND p.brand != ''
            GROUP BY p.brand ORDER BY total_matches DESC
        """).fetchall()
        brands = [{"brand": r["brand"], "matched_sources": r["matched_sources"],
                    "total_matches": r["total_matches"]} for r in brand_rows]

        # Recent pipeline runs
        runs = conn.execute(
            "SELECT * FROM pipeline_runs ORDER BY created_at DESC LIMIT 5"
        ).fetchall()
        recent_runs = [dict(r) for r in runs]

        # Confidence distribution
        conf_rows = conn.execute("""
            SELECT
                SUM(CASE WHEN confidence >= 0.95 THEN 1 ELSE 0 END) as excellent,
                SUM(CASE WHEN confidence >= 0.85 AND confidence < 0.95 THEN 1 ELSE 0 END) as high,
                SUM(CASE WHEN confidence >= 0.70 AND confidence < 0.85 THEN 1 ELSE 0 END) as medium,
                SUM(CASE WHEN confidence < 0.70 THEN 1 ELSE 0 END) as low
            FROM matches
        """).fetchone()
        confidence_dist = dict(conf_rows) if conf_rows else {}

        return {
            "source_count": stats["source_count"],
            "target_count": stats["target_count"],
            "match_count": stats["match_count"],
            "sources_matched": stats["sources_matched"],
            "coverage_pct": round(stats["sources_matched"] / stats["source_count"] * 100, 1) if stats["source_count"] else 0,
            "methods": methods,
            "brands": brands,
            "confidence_distribution": confidence_dist,
            "retailers": stats.get("retailers", []),
            "recent_runs": recent_runs,
        }
    finally:
        conn.close()


@app.get("/api/pipeline-history")
def pipeline_history():
    """Return history of pipeline runs."""
    conn = _get_db()
    try:
        rows = conn.execute(
            "SELECT * FROM pipeline_runs ORDER BY created_at DESC LIMIT 20"
        ).fetchall()
        runs = []
        for r in rows:
            run = dict(r)
            run["methods"] = json.loads(run.get("methods", "{}"))
            runs.append(run)
        return {"runs": runs, "total": len(runs)}
    finally:
        conn.close()


@app.post("/api/scrape/{reference}")
def scrape_single_product(reference: str):
    """Scrape hidden retailers for a single product on-demand. Great for live demos."""
    from .scraper import scrape_product
    from .fuzzy_match import verify_scraped_match
    from .models import Product

    conn = _get_db()
    try:
        product = get_product(conn, reference)
        if not product:
            return JSONResponse(status_code=404, content={"error": "Product not found"})
        if not product.get("is_source"):
            return JSONResponse(status_code=400, content={"error": "Can only scrape for source products"})

        src = Product.from_dict(product)
        raw_results = scrape_product(src)

        # Score each result
        scored = []
        for r in raw_results:
            score = verify_scraped_match(src, r["name"])
            scored.append({
                **r,
                "verification_score": round(score, 3),
                "verified": score >= 0.6,
            })

        scored.sort(key=lambda x: x["verification_score"], reverse=True)

        return {
            "reference": reference,
            "product_name": src.name,
            "total_results": len(scored),
            "verified_count": sum(1 for s in scored if s["verified"]),
            "retailers_found": list({r["retailer"] for r in scored}),
            "results": scored,
        }
    finally:
        conn.close()


@app.get("/api/scrape-results")
def get_scrape_results(source_reference: str | None = Query(None)):
    """View raw scrape results, optionally filtered by source."""
    conn = _get_db()
    try:
        if source_reference:
            rows = conn.execute(
                "SELECT * FROM scrape_results WHERE source_reference = ? ORDER BY created_at DESC",
                (source_reference,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM scrape_results ORDER BY created_at DESC LIMIT 100"
            ).fetchall()
        return {"results": [dict(r) for r in rows], "total": len(rows)}
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Embedding similarity endpoint (Claude #4)
# ---------------------------------------------------------------------------

_embeddings_cache: dict = {}


def _load_embeddings():
    """Load precomputed embeddings from data/embeddings/ (lazy, cached)."""
    if _embeddings_cache:
        return _embeddings_cache

    embeddings_dir = Path("data/embeddings")
    src_npy = embeddings_dir / "sources.npy"
    tgt_npy = embeddings_dir / "targets.npy"

    if not src_npy.exists() or not tgt_npy.exists():
        return None

    import numpy as np
    from .embedding_match import load_embeddings

    tgt_emb, tgt_refs = load_embeddings(embeddings_dir / "targets")
    src_emb, src_refs = load_embeddings(embeddings_dir / "sources")

    _embeddings_cache["target_embeddings"] = tgt_emb
    _embeddings_cache["target_refs"] = tgt_refs
    _embeddings_cache["source_embeddings"] = src_emb
    _embeddings_cache["source_refs"] = src_refs
    return _embeddings_cache


@app.get("/api/similar/{reference}")
def find_similar(reference: str, limit: int = Query(10, le=50), threshold: float = Query(0.80)):
    """Find semantically similar products using precomputed embeddings."""
    import numpy as np

    cache = _load_embeddings()
    if not cache:
        return JSONResponse(status_code=503, content={"error": "Embeddings not available. Run precomputation on GPU first."})

    # Find the reference in either source or target embeddings
    query_emb = None
    if reference in cache["source_refs"]:
        idx = cache["source_refs"].index(reference)
        query_emb = cache["source_embeddings"][idx]
    elif reference in cache["target_refs"]:
        idx = cache["target_refs"].index(reference)
        query_emb = cache["target_embeddings"][idx]

    if query_emb is None:
        return JSONResponse(status_code=404, content={"error": f"No embedding found for {reference}"})

    # Search against target embeddings
    tgt_emb = cache["target_embeddings"]
    scores = np.dot(tgt_emb, query_emb)
    top_indices = np.argsort(-scores)[:limit]

    conn = _get_db()
    try:
        results = []
        for idx in top_indices:
            score = float(scores[idx])
            if score < threshold:
                break
            ref = cache["target_refs"][idx]
            if ref == reference:
                continue
            product = get_product(conn, ref)
            if product:
                results.append({
                    "reference": ref,
                    "name": product["name"],
                    "brand": product.get("brand", ""),
                    "retailer": product.get("retailer", ""),
                    "price": product.get("price_eur"),
                    "similarity": round(score, 4),
                })
        return {"reference": reference, "similar": results, "count": len(results)}
    finally:
        conn.close()


_CHAT_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Product Matcher</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #0f172a; color: #e2e8f0; height: 100vh; display: flex; flex-direction: column; }
  header { padding: 16px 24px; background: #1e293b; border-bottom: 1px solid #334155; display: flex; align-items: center; gap: 16px; }
  header h1 { font-size: 18px; font-weight: 600; }
  .stats { font-size: 13px; color: #94a3b8; margin-left: auto; }
  .stats span { color: #22d3ee; font-weight: 600; }
  .main { flex: 1; display: flex; overflow: hidden; }
  .sidebar { width: 280px; background: #1e293b; border-right: 1px solid #334155; overflow-y: auto; padding: 12px; flex-shrink: 0; }
  .sidebar h3 { font-size: 12px; text-transform: uppercase; color: #64748b; margin-bottom: 8px; letter-spacing: 0.05em; }
  .source-item { padding: 8px 10px; border-radius: 6px; cursor: pointer; font-size: 13px; margin-bottom: 4px; transition: background 0.15s; }
  .source-item:hover { background: #334155; }
  .source-item.matched { border-left: 3px solid #22c55e; }
  .source-item.unmatched { border-left: 3px solid #ef4444; }
  .source-item .brand { color: #94a3b8; font-size: 11px; }
  .chat-area { flex: 1; display: flex; flex-direction: column; }
  .messages { flex: 1; overflow-y: auto; padding: 20px; }
  .msg { margin-bottom: 16px; max-width: 80%; }
  .msg.user { margin-left: auto; }
  .msg .bubble { padding: 10px 14px; border-radius: 12px; font-size: 14px; line-height: 1.5; }
  .msg.user .bubble { background: #3b82f6; color: white; border-bottom-right-radius: 4px; }
  .msg.bot .bubble { background: #1e293b; border: 1px solid #334155; border-bottom-left-radius: 4px; }
  .msg .bubble pre { white-space: pre-wrap; font-family: inherit; }
  .input-area { padding: 16px 20px; background: #1e293b; border-top: 1px solid #334155; display: flex; gap: 10px; }
  .input-area input { flex: 1; background: #0f172a; border: 1px solid #334155; border-radius: 8px; padding: 10px 14px; color: #e2e8f0; font-size: 14px; outline: none; }
  .input-area input:focus { border-color: #3b82f6; }
  .input-area button { background: #3b82f6; color: white; border: none; border-radius: 8px; padding: 10px 20px; font-size: 14px; cursor: pointer; }
  .input-area button:hover { background: #2563eb; }
  .input-area button:disabled { opacity: 0.5; cursor: not-allowed; }
  .match-card { background: #0f172a; border: 1px solid #334155; border-radius: 8px; padding: 10px; margin-top: 8px; font-size: 13px; }
  .match-card .method { display: inline-block; background: #334155; padding: 2px 6px; border-radius: 4px; font-size: 11px; }
  .confidence { color: #22c55e; }
  @media (max-width: 768px) { .sidebar { display: none; } }
</style>
</head>
<body>
<header>
  <h1>Product Matcher</h1>
  <div class="stats" id="stats">Loading...</div>
</header>
<div class="main">
  <div class="sidebar" id="sidebar"></div>
  <div class="chat-area">
    <div class="messages" id="messages">
      <div class="msg bot"><div class="bubble">Welcome! Ask me about products, matches, or brands. Try:<br>- "Show Samsung sources"<br>- "Which products are unmatched?"<br>- "Search for LG 32 inch TV"</div></div>
    </div>
    <div class="input-area">
      <input type="text" id="input" placeholder="Search products or ask a question..." autofocus>
      <button id="send" onclick="sendMessage()">Send</button>
    </div>
  </div>
</div>
<script>
const msgs = document.getElementById('messages');
const input = document.getElementById('input');
const history = [];

input.addEventListener('keydown', e => { if (e.key === 'Enter') sendMessage(); });

async function sendMessage() {
  const text = input.value.trim();
  if (!text) return;
  input.value = '';
  addMsg('user', text);
  document.getElementById('send').disabled = true;
  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({message: text, history: history.slice(-10)})
    });
    const data = await res.json();
    history.push({role: 'user', content: text});
    history.push({role: 'assistant', content: data.reply});
    addMsg('bot', data.reply);
  } catch(e) {
    addMsg('bot', 'Error: ' + e.message);
  }
  document.getElementById('send').disabled = false;
  input.focus();
}

function addMsg(role, text) {
  const d = document.createElement('div');
  d.className = 'msg ' + role;
  d.innerHTML = '<div class="bubble"><pre>' + escHtml(text) + '</pre></div>';
  msgs.appendChild(d);
  msgs.scrollTop = msgs.scrollHeight;
}

function escHtml(s) {
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

async function loadStats() {
  try {
    const res = await fetch('/api/stats');
    const s = await res.json();
    document.getElementById('stats').innerHTML =
      `<span>${s.sources_matched}</span>/${s.source_count} matched | <span>${s.match_count}</span> links | ${Object.keys(s.methods).length} strategies`;
  } catch(e) {}
}

async function loadSidebar() {
  try {
    const res = await fetch('/api/sources');
    const data = await res.json();
    const sb = document.getElementById('sidebar');
    sb.innerHTML = '<h3>Source Products</h3>';
    data.sources.forEach(s => {
      const cls = s.match_count > 0 ? 'matched' : 'unmatched';
      const d = document.createElement('div');
      d.className = 'source-item ' + cls;
      d.innerHTML = `${escHtml(s.name.substring(0,40))}${s.name.length>40?'...':''}<br><span class="brand">${s.brand} | ${s.match_count} matches</span>`;
      d.onclick = () => { input.value = s.name.substring(0,50); sendMessage(); };
      sb.appendChild(d);
    });
  } catch(e) {}
}

loadStats();
loadSidebar();
</script>
</body>
</html>"""

# ---------------------------------------------------------------------------
# Reusability & "wow factor" endpoints (Claude #3)
# ---------------------------------------------------------------------------

@app.get("/api/product-types")
def get_product_types():
    """Return the product type taxonomy the system knows about."""
    from .fuzzy_match import PRODUCT_TYPES
    types = []
    for ptype, keywords in PRODUCT_TYPES.items():
        # Group by category prefix
        category = ptype.split("_")[0] if "_" in ptype else ptype
        types.append({
            "type_id": ptype,
            "category": category,
            "keywords": keywords,
            "keyword_count": len(keywords),
        })
    # Group by category
    by_category: dict[str, list] = {}
    for t in types:
        by_category.setdefault(t["category"], []).append(t)
    return {
        "total_types": len(types),
        "categories": {k: len(v) for k, v in by_category.items()},
        "types": types,
    }


@app.get("/api/match-quality")
def match_quality(category: str | None = Query(None)):
    """Return precision/recall/F1 estimates per category using known correct links."""
    data_dir = Path("data")
    correct_files = {
        "tv_audio": data_dir / "correct_links.json",
        "small_appliances": data_dir / "correct_links_small_appliances.json",
    }

    conn = _get_db()
    try:
        results = {}
        for cat, path in correct_files.items():
            if category and cat != category:
                continue
            if not path.exists():
                continue
            with open(path) as f:
                correct: dict[str, list[str]] = json.load(f)

            # Get our matches from DB for this category's sources
            our_links: dict[str, set[str]] = {}
            for source_ref in correct:
                matches = get_matches_for_source(conn, source_ref)
                our_links[source_ref] = {m["target_reference"] for m in matches}

            # Compute metrics
            total_correct = sum(len(v) for v in correct.values())
            total_submitted = sum(len(v) for v in our_links.values())
            true_positives = 0
            false_positives = 0
            false_negatives = 0

            per_source = []
            for source_ref, correct_targets in correct.items():
                correct_set = set(correct_targets)
                our_set = our_links.get(source_ref, set())
                tp = len(correct_set & our_set)
                fp = len(our_set - correct_set)
                fn = len(correct_set - our_set)
                true_positives += tp
                false_positives += fp
                false_negatives += fn
                per_source.append({
                    "source_reference": source_ref,
                    "correct": len(correct_set),
                    "submitted": len(our_set),
                    "true_positives": tp,
                    "false_positives": fp,
                    "missed": fn,
                })

            precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) else 0
            recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) else 0
            f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0
            coverage = sum(1 for s in our_links.values() if s) / len(correct) if correct else 0
            # Scoring formula: 0.6 * recall + 0.2 * precision + 0.2 * coverage
            score = 0.6 * recall + 0.2 * precision + 0.2 * coverage

            results[cat] = {
                "sources": len(correct),
                "total_correct_links": total_correct,
                "total_submitted_links": total_submitted,
                "true_positives": true_positives,
                "false_positives": false_positives,
                "false_negatives": false_negatives,
                "precision": round(precision, 4),
                "recall": round(recall, 4),
                "f1": round(f1, 4),
                "coverage": round(coverage, 4),
                "estimated_score": round(score * 50, 1),
                "per_source": sorted(per_source, key=lambda x: x["missed"], reverse=True),
            }

        return {"categories": results}
    finally:
        conn.close()


@app.get("/api/compare/{ref1}/{ref2}")
def compare_products(ref1: str, ref2: str):
    """Side-by-side comparison of two products with all attributes."""
    from .fuzzy_match import (
        extract_model_number, _extract_screen_size, _classify_product_type,
    )
    from .models import Product

    conn = _get_db()
    try:
        p1_raw = get_product(conn, ref1)
        p2_raw = get_product(conn, ref2)
        if not p1_raw or not p2_raw:
            missing = ref1 if not p1_raw else ref2
            return JSONResponse(status_code=404, content={"error": f"Product {missing} not found"})

        p1 = Product.from_dict(p1_raw)
        p2 = Product.from_dict(p2_raw)

        def _product_info(p: Product, raw: dict) -> dict:
            specs = raw.get("specifications", {})
            if isinstance(specs, str):
                specs = json.loads(specs)
            return {
                "reference": p.reference,
                "name": p.name,
                "brand": p.brand,
                "category": p.category,
                "ean": p.ean,
                "price_eur": p.price_eur,
                "retailer": p.retailer,
                "url": p.url,
                "image_url": raw.get("image_url"),
                "model_number": extract_model_number(p),
                "screen_size": _extract_screen_size(p.name),
                "product_type": _classify_product_type(p.name),
                "specifications": specs,
                "is_source": bool(raw.get("is_source")),
            }

        info1 = _product_info(p1, p1_raw)
        info2 = _product_info(p2, p2_raw)

        # Check if they're matched
        match_row = conn.execute(
            "SELECT * FROM matches WHERE (source_reference = ? AND target_reference = ?) "
            "OR (source_reference = ? AND target_reference = ?)",
            (ref1, ref2, ref2, ref1)
        ).fetchone()

        # Find shared and different specs
        specs1 = info1["specifications"]
        specs2 = info2["specifications"]
        all_keys = sorted(set(list(specs1.keys()) + list(specs2.keys())))
        spec_comparison = []
        for k in all_keys:
            v1 = specs1.get(k)
            v2 = specs2.get(k)
            spec_comparison.append({
                "key": k,
                "product_1": v1,
                "product_2": v2,
                "match": v1 == v2 if v1 and v2 else None,
            })

        return {
            "product_1": info1,
            "product_2": info2,
            "match_info": dict(match_row) if match_row else None,
            "same_brand": info1["brand"] and info2["brand"] and info1["brand"].lower() == info2["brand"].lower(),
            "same_screen_size": info1["screen_size"] == info2["screen_size"] if info1["screen_size"] and info2["screen_size"] else None,
            "same_product_type": info1["product_type"] == info2["product_type"] if info1["product_type"] and info2["product_type"] else None,
            "spec_comparison": spec_comparison,
        }
    finally:
        conn.close()


# SPA catch-all: serve index.html for client-side routes (must be after all API routes)
@app.get("/{full_path:path}", response_class=HTMLResponse)
def spa_fallback(full_path: str):
    """Serve React index.html for all non-API paths (SPA client-side routing)."""
    if full_path.startswith("api/"):
        return JSONResponse(status_code=404, content={"error": "Not found"})
    index = _WEBAPP_DIST / "index.html"
    if index.exists():
        return index.read_text()
    return _CHAT_HTML


# Mount React frontend static assets (must be after all API routes)
if _WEBAPP_DIST.exists():
    app.mount("/assets", StaticFiles(directory=str(_WEBAPP_DIST / "assets")), name="static")
