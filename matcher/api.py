"""REST API for the product matcher.

Provides endpoints for searching products, viewing matches,
running the pipeline, chat-based search, and exporting submissions.
"""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, File, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
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


def _get_db():
    conn = get_connection()
    init_db(conn)
    return conn


@app.get("/", response_class=HTMLResponse)
def ui():
    """Serve the product matcher chat UI."""
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
