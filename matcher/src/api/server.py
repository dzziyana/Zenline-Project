import asyncio

from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.matching.pipeline import run_matching_pipeline
from src.models.product import SourceProduct, TargetProduct, SourceProductSubmission
from src.scraping.base_scraper import BaseScraper
from src.scraping.expert_scraper import ExpertScraper
from src.scraping.cyberport_scraper import CyberportScraper
from src.scraping.electronic4you_scraper import Electronic4youScraper
from src.scraping.etec_scraper import EtecScraper
from src.utils.data_loader import (
    load_source_products,
    load_target_pool,
    save_submission,
)

app = FastAPI(title="Zenline Product Matcher", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:8080"],
    allow_methods=["*"],
    allow_headers=["*"],
)

SCRAPERS: dict[str, BaseScraper] = {
    "expert": ExpertScraper(),
    "cyberport": CyberportScraper(),
    "electronic4you": Electronic4youScraper(),
    "etec": EtecScraper(),
}


class MatchRequest(BaseModel):
    category: str
    use_llm: bool = False
    fuzzy_threshold: float = 75.0


class ScrapeRequest(BaseModel):
    ean: str | None = None
    name: str
    retailers: list[str] = []


class MatchResult(BaseModel):
    category: str
    total_sources: int
    total_matches: int
    submissions: list[SourceProductSubmission]


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/categories")
async def list_categories():
    """List available categories based on downloaded data files."""
    from pathlib import Path

    data_dir = Path(__file__).parent.parent.parent / "data"
    categories = []
    for f in data_dir.glob("source_products_*.json"):
        cat = f.stem.replace("source_products_", "")
        categories.append(cat)
    return {"categories": sorted(categories)}


@app.get("/products/source/{category}")
async def get_source_products(category: str):
    try:
        products = load_source_products(category)
        return {"category": category, "count": len(products), "products": products}
    except FileNotFoundError:
        raise HTTPException(404, f"Category '{category}' not found")


@app.get("/products/target/{category}")
async def get_target_products(category: str):
    try:
        products = load_target_pool(category)
        return {"category": category, "count": len(products), "products": products}
    except FileNotFoundError:
        raise HTTPException(404, f"Category '{category}' not found")


@app.post("/match", response_model=MatchResult)
async def match_products(request: MatchRequest):
    try:
        sources = load_source_products(request.category)
        targets = load_target_pool(request.category)
    except FileNotFoundError:
        raise HTTPException(404, f"Category '{request.category}' not found")

    submissions = run_matching_pipeline(
        sources, targets, use_llm=request.use_llm, fuzzy_threshold=request.fuzzy_threshold
    )

    total_matches = sum(len(s.competitors) for s in submissions)
    save_submission(submissions, request.category)

    return MatchResult(
        category=request.category,
        total_sources=len(sources),
        total_matches=total_matches,
        submissions=submissions,
    )


@app.post("/scrape")
async def scrape_product(request: ScrapeRequest):
    retailer_keys = request.retailers or list(SCRAPERS.keys())
    results = {}

    for key in retailer_keys:
        scraper = SCRAPERS.get(key)
        if not scraper:
            continue
        try:
            products = await scraper.search_product(request.ean, request.name)
            results[key] = [p.model_dump() for p in products]
        except Exception as e:
            results[key] = {"error": str(e)}

    return {"query": request.model_dump(), "results": results}


@app.post("/upload/source/{category}")
async def upload_source_data(category: str, file: UploadFile):
    """Upload source products JSON for a category."""
    import json
    from pathlib import Path

    data_dir = Path(__file__).parent.parent.parent / "data"
    data_dir.mkdir(exist_ok=True)

    content = await file.read()
    data = json.loads(content)
    path = data_dir / f"source_products_{category}.json"
    with open(path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    return {"message": f"Uploaded {len(data)} source products for {category}"}


@app.post("/upload/target/{category}")
async def upload_target_data(category: str, file: UploadFile):
    """Upload target pool JSON for a category."""
    import json
    from pathlib import Path

    data_dir = Path(__file__).parent.parent.parent / "data"
    data_dir.mkdir(exist_ok=True)

    content = await file.read()
    data = json.loads(content)
    path = data_dir / f"target_pool_{category}.json"
    with open(path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    return {"message": f"Uploaded {len(data)} target products for {category}"}
