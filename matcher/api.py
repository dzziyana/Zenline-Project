"""REST API for the product matcher.

Provides endpoints for searching products, viewing matches,
running the pipeline, chat-based search, and exporting submissions.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import anthropic
from fastapi import FastAPI, Query
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
        insert_products(conn, sources, is_source=True)
        insert_products(conn, targets, is_source=False)
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
