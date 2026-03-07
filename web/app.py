"""Web UI for product matching - demo interface for jury."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, UploadFile, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from matcher.models import Product
from matcher.ean_match import match_by_ean
from matcher.fuzzy_match import match_by_model_number, match_by_fuzzy_name
from matcher.pipeline import dedupe_matches, build_submission, run_matching
from matcher.scraper import scrape_product

app = FastAPI(title="Product Matcher")

DATA_DIR = Path("data")
OUTPUT_DIR = Path("output")

# In-memory state
_sources: list[Product] = []
_targets: list[Product] = []
_matches: list = []


@app.get("/", response_class=HTMLResponse)
async def index():
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Product Matcher</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }
    </style>
</head>
<body class="bg-slate-50 min-h-screen">
    <nav class="bg-white border-b border-slate-200 px-6 py-4">
        <div class="max-w-6xl mx-auto flex items-center gap-4">
            <h1 class="text-xl font-bold text-slate-900">Product Matcher</h1>
            <span class="text-sm text-slate-400">Zenline Hackathon</span>
        </div>
    </nav>
    <main class="max-w-6xl mx-auto px-6 py-8" id="app">
        <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
            <div class="bg-white rounded-xl border border-slate-200 p-5">
                <h2 class="font-semibold text-slate-900 mb-3">1. Load Data</h2>
                <div class="space-y-3">
                    <div>
                        <label class="block text-sm text-slate-600 mb-1">Source Products JSON</label>
                        <input type="file" id="sourceFile" accept=".json" class="text-sm">
                    </div>
                    <div>
                        <label class="block text-sm text-slate-600 mb-1">Target Pool JSON</label>
                        <input type="file" id="targetFile" accept=".json" class="text-sm">
                    </div>
                    <button onclick="loadData()" class="w-full px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700">
                        Load Data
                    </button>
                    <div id="loadStatus" class="text-sm text-slate-500"></div>
                </div>
            </div>
            <div class="bg-white rounded-xl border border-slate-200 p-5">
                <h2 class="font-semibold text-slate-900 mb-3">2. Run Matching</h2>
                <div class="space-y-3">
                    <label class="flex items-center gap-2 text-sm text-slate-600">
                        <input type="checkbox" id="doScrape" checked> Include web scraping
                    </label>
                    <button onclick="runMatch()" class="w-full px-4 py-2 bg-emerald-600 text-white rounded-lg text-sm font-medium hover:bg-emerald-700">
                        Run Pipeline
                    </button>
                    <div id="matchStatus" class="text-sm text-slate-500"></div>
                </div>
            </div>
            <div class="bg-white rounded-xl border border-slate-200 p-5">
                <h2 class="font-semibold text-slate-900 mb-3">3. Export</h2>
                <button onclick="downloadResults()" class="w-full px-4 py-2 bg-amber-600 text-white rounded-lg text-sm font-medium hover:bg-amber-700">
                    Download Submission JSON
                </button>
            </div>
        </div>

        <div class="bg-white rounded-xl border border-slate-200 p-5 mb-6">
            <h2 class="font-semibold text-slate-900 mb-3">Search Products</h2>
            <div class="flex gap-3">
                <input type="text" id="searchQuery" placeholder="Search by name, EAN, brand..."
                    class="flex-1 px-4 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:border-indigo-500">
                <button onclick="searchProducts()" class="px-6 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700">
                    Search
                </button>
            </div>
            <div id="searchResults" class="mt-4"></div>
        </div>

        <div id="matchResults" class="bg-white rounded-xl border border-slate-200 p-5">
            <h2 class="font-semibold text-slate-900 mb-3">Match Results</h2>
            <div id="resultsTable" class="text-sm text-slate-500">Load data and run matching to see results.</div>
        </div>
    </main>

    <script>
    async function loadData() {
        const sourceFile = document.getElementById('sourceFile').files[0];
        const targetFile = document.getElementById('targetFile').files[0];
        const status = document.getElementById('loadStatus');

        if (!sourceFile || !targetFile) {
            status.textContent = 'Please select both files.';
            return;
        }

        const formData = new FormData();
        formData.append('source_file', sourceFile);
        formData.append('target_file', targetFile);

        status.textContent = 'Loading...';
        const resp = await fetch('/api/load', { method: 'POST', body: formData });
        const data = await resp.json();
        status.textContent = `Loaded ${data.sources} sources, ${data.targets} targets`;
    }

    async function runMatch() {
        const status = document.getElementById('matchStatus');
        const doScrape = document.getElementById('doScrape').checked;
        status.textContent = 'Running pipeline...';

        const resp = await fetch(`/api/match?scrape=${doScrape}`, { method: 'POST' });
        const data = await resp.json();
        status.textContent = `Found ${data.total_matches} matches for ${data.sources_matched} products`;

        renderResults(data);
    }

    function renderResults(data) {
        const container = document.getElementById('resultsTable');
        if (!data.summary || data.summary.length === 0) {
            container.innerHTML = '<p class="text-slate-400">No matches found.</p>';
            return;
        }

        let html = '<table class="w-full text-left text-sm"><thead><tr class="border-b border-slate-200">';
        html += '<th class="py-2 px-2">Source Product</th><th class="py-2 px-2">Matches</th><th class="py-2 px-2">Methods</th>';
        html += '</tr></thead><tbody>';

        for (const item of data.summary) {
            html += `<tr class="border-b border-slate-100 hover:bg-slate-50">`;
            html += `<td class="py-2 px-2 font-medium">${item.source_name}</td>`;
            html += `<td class="py-2 px-2">${item.match_count}</td>`;
            html += `<td class="py-2 px-2 text-slate-400">${item.methods.join(', ')}</td>`;
            html += `</tr>`;
        }
        html += '</tbody></table>';
        container.innerHTML = html;
    }

    async function searchProducts() {
        const query = document.getElementById('searchQuery').value;
        const resp = await fetch(`/api/search?q=${encodeURIComponent(query)}`);
        const data = await resp.json();

        const container = document.getElementById('searchResults');
        if (data.results.length === 0) {
            container.innerHTML = '<p class="text-sm text-slate-400">No results found.</p>';
            return;
        }

        let html = '<div class="space-y-2">';
        for (const p of data.results) {
            html += `<div class="p-3 bg-slate-50 rounded-lg">`;
            html += `<p class="font-medium text-slate-900">${p.name}</p>`;
            html += `<p class="text-xs text-slate-400">${p.reference} | ${p.brand || ''} | EAN: ${p.ean || 'N/A'} | ${p.type}</p>`;
            html += `</div>`;
        }
        html += '</div>';
        container.innerHTML = html;
    }

    async function downloadResults() {
        const resp = await fetch('/api/export');
        const blob = await resp.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'submission.json';
        a.click();
        URL.revokeObjectURL(url);
    }
    </script>
</body>
</html>
"""


@app.post("/api/load")
async def load_data(source_file: UploadFile, target_file: UploadFile):
    global _sources, _targets
    source_data = json.loads(await source_file.read())
    target_data = json.loads(await target_file.read())
    _sources = [Product.from_dict(d) for d in source_data]
    _targets = [Product.from_dict(d) for d in target_data]
    return {"sources": len(_sources), "targets": len(_targets)}


@app.post("/api/match")
async def match(scrape: bool = True):
    global _matches
    if not _sources:
        raise HTTPException(400, "No source products loaded")

    matches = run_matching(_sources, _targets, do_scrape=scrape)
    _matches = matches

    # Build summary
    by_source: dict[str, list] = {}
    source_names = {s.reference: s.name for s in _sources}
    for m in matches:
        by_source.setdefault(m.source_reference, []).append(m)

    summary = []
    for ref, match_list in by_source.items():
        methods = list({m.method for m in match_list})
        summary.append({
            "source_reference": ref,
            "source_name": source_names.get(ref, ref),
            "match_count": len(match_list),
            "methods": methods,
        })
    summary.sort(key=lambda x: x["match_count"], reverse=True)

    return {
        "total_matches": len(matches),
        "sources_matched": len(by_source),
        "total_sources": len(_sources),
        "summary": summary,
    }


@app.get("/api/search")
async def search(q: str = ""):
    if not q:
        return {"results": []}

    q_lower = q.lower()
    results = []

    for s in _sources:
        if q_lower in s.name.lower() or q_lower == (s.ean or "") or q_lower in s.brand.lower():
            results.append({**vars(s), "type": "source"})
    for t in _targets:
        if q_lower in t.name.lower() or q_lower == (t.ean or "") or q_lower in t.brand.lower():
            results.append({**vars(t), "type": "target"})

    return {"results": results[:50]}


@app.get("/api/export")
async def export():
    if not _matches:
        raise HTTPException(400, "No matches to export. Run matching first.")
    submission = build_submission(_matches)
    return JSONResponse(content=submission)
