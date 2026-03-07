"""REST API for the product matcher.

Provides endpoints for searching products, viewing matches,
running the pipeline, chat-based search, and exporting submissions.
"""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, File, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
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

app = FastAPI(title="Product Matcher API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _get_db():
    conn = get_connection()
    init_db(conn)
    return conn


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
        if not product:
            return JSONResponse(status_code=404, content={"error": "Product not found"})
        matches = get_matches_for_source(conn, reference)
        return {"product": product, "matches": matches}
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
        return {"results": results, "total": len(results), "query": q}
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


@app.get("/api/submission")
def get_submission():
    """Export current matches as submission JSON."""
    conn = _get_db()
    try:
        sources = get_all_sources(conn)
        submission = []
        for s in sources:
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
    finally:
        conn.close()


@app.post("/api/run")
def run_pipeline_endpoint(
    category: str = Query("TV & Audio"),
    scrape: bool = Query(False),
):
    """Trigger a pipeline run."""
    from .pipeline import load_products, run_matching, dedupe_matches
    from .db import insert_products, insert_matches, log_pipeline_run

    data_dir = Path("data")
    safe_name = category.lower().replace(" & ", "_").replace(" ", "_")
    source_path = data_dir / f"source_products_{safe_name}.json"
    target_path = data_dir / f"target_products_{safe_name}.json"

    if not source_path.exists() or not target_path.exists():
        return JSONResponse(status_code=404, content={"error": f"Data not found for category: {category}"})

    sources = load_products(source_path)
    targets = load_products(target_path)
    matches = run_matching(sources, targets, do_scrape=scrape)

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
- Brands: Samsung, LG, Sharp, TCL, CHIQ, PEAQ, Xiaomi, Sony, Philips, Hisense, Sonos, JBL, Bose
- Retailers: Amazon AT, MediaMarkt AT
- Category: TV & Audio (TVs, soundbars, audio cables)

Respond in the same language the user writes in (German or English)."""


def _chat_search(query: str) -> str:
    """Search the DB and format results for the chat context."""
    conn = _get_db()
    try:
        results = search_products(conn, query, limit=10)
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
    except Exception as e:
        reply = f"AI chat unavailable ({type(e).__name__}). Here are the raw search results:\n\n{search_context}"

    return {"reply": reply, "search_results": search_context}


@app.post("/api/upload")
async def upload_data(
    sources: UploadFile = File(...),
    targets: UploadFile = File(...),
    category: str = Query("uploaded"),
):
    """Upload new source and target JSON files and run the pipeline."""
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
