"""Web scraping for hidden retailers."""

from __future__ import annotations

import asyncio
import time

import httpx
from selectolax.parser import HTMLParser

from .models import Match, Product

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) ProductMatcherBot/1.0 (hackathon project)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "de-AT,de;q=0.9,en;q=0.8",
}

# Rate limiting: track last request time per domain
_last_request: dict[str, float] = {}
MIN_DELAY = 1.0  # seconds between requests to same domain


async def _rate_limit(domain: str):
    """Ensure we don't hit the same domain too fast."""
    now = time.time()
    last = _last_request.get(domain, 0)
    wait = MIN_DELAY - (now - last)
    if wait > 0:
        await asyncio.sleep(wait)
    _last_request[domain] = time.time()


async def fetch_page(client: httpx.AsyncClient, url: str, domain: str) -> str | None:
    """Fetch a page with rate limiting."""
    await _rate_limit(domain)
    try:
        resp = await client.get(url, headers=HEADERS, follow_redirects=True, timeout=15)
        if resp.status_code == 200:
            return resp.text
    except (httpx.HTTPError, httpx.TimeoutException):
        pass
    return None


async def search_expert_at(client: httpx.AsyncClient, query: str) -> list[dict]:
    """Search expert.at for products."""
    domain = "expert.at"
    url = f"https://www.expert.at/search?query={httpx.QueryParams({'query': query})}"
    # expert.at uses query param 'query'
    search_url = f"https://www.expert.at/search?query={query}"
    html = await fetch_page(client, search_url, domain)
    if not html:
        return []
    return _parse_expert_results(html)


def _parse_expert_results(html: str) -> list[dict]:
    """Parse expert.at search results."""
    tree = HTMLParser(html)
    results = []
    # This is a placeholder - actual selectors need to be determined
    # by inspecting the live site during the hackathon
    for node in tree.css("div.product-item, article.product, div[data-product]"):
        name_el = node.css_first("h2, h3, .product-name, .product-title")
        price_el = node.css_first(".price, .product-price, [data-price]")
        link_el = node.css_first("a[href]")
        if name_el:
            result = {
                "name": name_el.text(strip=True),
                "url": "",
                "price": None,
                "retailer": "Expert AT",
            }
            if link_el:
                href = link_el.attributes.get("href", "")
                if href and not href.startswith("http"):
                    href = f"https://www.expert.at{href}"
                result["url"] = href
            if price_el:
                price_text = price_el.text(strip=True)
                result["price"] = _parse_price(price_text)
            results.append(result)
    return results


async def search_cyberport_at(client: httpx.AsyncClient, query: str) -> list[dict]:
    """Search cyberport.at for products."""
    domain = "cyberport.at"
    search_url = f"https://www.cyberport.at/search.html?q={query}"
    html = await fetch_page(client, search_url, domain)
    if not html:
        return []
    return _parse_cyberport_results(html)


def _parse_cyberport_results(html: str) -> list[dict]:
    """Parse cyberport.at search results."""
    tree = HTMLParser(html)
    results = []
    for node in tree.css("div.productList__item, article.product, .product-item"):
        name_el = node.css_first("h2, h3, .product-name, .product-title, a.product-link")
        price_el = node.css_first(".price, .product-price")
        link_el = node.css_first("a[href]")
        if name_el:
            result = {
                "name": name_el.text(strip=True),
                "url": "",
                "price": None,
                "retailer": "Cyberport AT",
            }
            if link_el:
                href = link_el.attributes.get("href", "")
                if href and not href.startswith("http"):
                    href = f"https://www.cyberport.at{href}"
                result["url"] = href
            if price_el:
                result["price"] = _parse_price(price_el.text(strip=True))
            results.append(result)
    return results


async def search_electronic4you(client: httpx.AsyncClient, query: str) -> list[dict]:
    """Search electronic4you.at for products."""
    domain = "electronic4you.at"
    search_url = f"https://www.electronic4you.at/search?sSearch={query}"
    html = await fetch_page(client, search_url, domain)
    if not html:
        return []
    return _parse_electronic4you_results(html)


def _parse_electronic4you_results(html: str) -> list[dict]:
    """Parse electronic4you.at search results."""
    tree = HTMLParser(html)
    results = []
    for node in tree.css(".product--box, .product-item, article.product"):
        name_el = node.css_first(".product--title, .product-name, h2, h3")
        price_el = node.css_first(".product--price, .price")
        link_el = node.css_first("a[href]")
        if name_el:
            result = {
                "name": name_el.text(strip=True),
                "url": "",
                "price": None,
                "retailer": "electronic4you.at",
            }
            if link_el:
                href = link_el.attributes.get("href", "")
                if href and not href.startswith("http"):
                    href = f"https://www.electronic4you.at{href}"
                result["url"] = href
            if price_el:
                result["price"] = _parse_price(price_el.text(strip=True))
            results.append(result)
    return results


async def search_etec(client: httpx.AsyncClient, query: str) -> list[dict]:
    """Search e-tec.at for products."""
    domain = "e-tec.at"
    search_url = f"https://www.e-tec.at/search?q={query}"
    html = await fetch_page(client, search_url, domain)
    if not html:
        return []
    return _parse_etec_results(html)


def _parse_etec_results(html: str) -> list[dict]:
    """Parse e-tec.at search results."""
    tree = HTMLParser(html)
    results = []
    for node in tree.css(".product-item, article.product, .productList-item"):
        name_el = node.css_first("h2, h3, .product-name, .product-title")
        price_el = node.css_first(".price, .product-price")
        link_el = node.css_first("a[href]")
        if name_el:
            result = {
                "name": name_el.text(strip=True),
                "url": "",
                "price": None,
                "retailer": "E-Tec",
            }
            if link_el:
                href = link_el.attributes.get("href", "")
                if href and not href.startswith("http"):
                    href = f"https://www.e-tec.at{href}"
                result["url"] = href
            if price_el:
                result["price"] = _parse_price(price_el.text(strip=True))
            results.append(result)
    return results


def _parse_price(text: str) -> float | None:
    """Parse a price string like '€ 1.299,00' or '1299.00' into a float."""
    import re
    text = text.replace("€", "").replace("\xa0", "").strip()
    # Handle European format: 1.299,00
    match = re.search(r'([\d.]+),(\d{2})', text)
    if match:
        whole = match.group(1).replace(".", "")
        cents = match.group(2)
        return float(f"{whole}.{cents}")
    # Handle standard format: 1299.00
    match = re.search(r'([\d,]+)\.(\d{2})', text)
    if match:
        whole = match.group(1).replace(",", "")
        cents = match.group(2)
        return float(f"{whole}.{cents}")
    # Just digits
    match = re.search(r'(\d+)', text)
    if match:
        return float(match.group(1))
    return None


SCRAPERS = {
    "Expert AT": search_expert_at,
    "Cyberport AT": search_cyberport_at,
    "electronic4you.at": search_electronic4you,
    "E-Tec": search_etec,
}


async def scrape_product(source: Product) -> list[Match]:
    """Search all hidden retailers for a single source product."""
    matches = []
    queries = _build_search_queries(source)

    async with httpx.AsyncClient() as client:
        for retailer_name, search_fn in SCRAPERS.items():
            for query in queries:
                results = await search_fn(client, query)
                for r in results:
                    # Generate a reference for scraped products
                    ref = f"SCRAPED_{retailer_name.replace(' ', '_')}_{hash(r['url']) % 10**8:08d}"
                    matches.append(Match(
                        source_reference=source.reference,
                        target_reference=ref,
                        target_name=r["name"],
                        target_retailer=retailer_name,
                        target_url=r.get("url", ""),
                        target_price=r.get("price"),
                        confidence=0.7,
                        method="scrape",
                    ))
                if results:
                    break  # Found results with this query, skip remaining queries

    return matches


def _build_search_queries(source: Product) -> list[str]:
    """Build search queries in priority order."""
    queries = []
    if source.ean:
        queries.append(source.ean)
    # Brand + model number
    from .fuzzy_match import extract_model_number
    model = extract_model_number(source.name)
    if model and source.brand:
        queries.append(f"{source.brand} {model}")
    # Full name
    queries.append(source.name)
    return queries


async def scrape_all(sources: list[Product], max_concurrent: int = 3) -> list[Match]:
    """Scrape all hidden retailers for all source products."""
    semaphore = asyncio.Semaphore(max_concurrent)
    all_matches = []

    async def _scrape_one(source: Product):
        async with semaphore:
            return await scrape_product(source)

    tasks = [_scrape_one(s) for s in sources]
    results = await asyncio.gather(*tasks)
    for result in results:
        all_matches.extend(result)

    return all_matches
