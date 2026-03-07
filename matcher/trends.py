"""Trend intelligence scraper.

Scrapes tech journals, review sites, and social media to identify
trending electronics products and the qualities driving their popularity.
Uses Claude to analyze and extract structured insights.
"""

from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass, field, asdict
from urllib.parse import quote_plus

from selectolax.parser import HTMLParser

try:
    from curl_cffi import requests as cffi_requests
except ImportError:
    cffi_requests = None

import httpx

MIN_DELAY = 2.0
_last_request: dict[str, float] = {}


def _rate_limit(domain: str):
    now = time.time()
    last = _last_request.get(domain, 0)
    wait = MIN_DELAY - (now - last)
    if wait > 0:
        time.sleep(wait)
    _last_request[domain] = time.time()


def _fetch(url: str, domain: str) -> str | None:
    _rate_limit(domain)
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,de;q=0.8",
    }
    try:
        if cffi_requests:
            r = cffi_requests.get(url, headers=headers, impersonate="chrome", timeout=15)
            if r.status_code == 200:
                return r.text
        else:
            r = httpx.get(url, headers=headers, timeout=15, follow_redirects=True)
            if r.status_code == 200:
                return r.text
    except Exception:
        pass
    return None


@dataclass
class TrendArticle:
    title: str
    snippet: str
    source: str
    url: str
    category: str = ""


@dataclass
class TrendInsight:
    product_name: str
    brand: str
    category: str
    trend_score: int  # 1-10
    qualities: list[str] = field(default_factory=list)
    sentiment: str = "positive"  # positive, neutral, negative
    sources: list[str] = field(default_factory=list)
    summary: str = ""


# ---- Scraping Sources ----

TECH_QUERIES = [
    "best TV 2025 2026 review",
    "trending headphones earbuds 2025 2026",
    "best smart TV QLED OLED comparison",
    "Samsung LG Sony TV review 2025",
    "best wireless earbuds 2025 2026",
    "trending electronics Austria",
    "beste Fernseher 2025 Test",
    "beste Kopfhörer 2025 Vergleich",
]

REDDIT_QUERIES = [
    ("television", "best TV 2025"),
    ("headphones", "best earbuds 2025"),
    ("hometheater", "trending TV"),
    ("gadgets", "trending electronics 2025"),
]


def _scrape_duckduckgo_news(query: str, max_results: int = 8) -> list[TrendArticle]:
    """Scrape DuckDuckGo news search - more reliable than Google."""
    url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
    html = _fetch(url, "duckduckgo.com")
    if not html:
        return []

    tree = HTMLParser(html)
    articles = []

    for node in tree.css("div.result, div.links_main"):
        title_el = node.css_first("a.result__a, h2 a")
        snippet_el = node.css_first("a.result__snippet, div.result__snippet")

        title = title_el.text(strip=True) if title_el else ""
        snippet = snippet_el.text(strip=True) if snippet_el else ""
        href = title_el.attributes.get("href", "") if title_el else ""

        if title and len(title) > 10:
            articles.append(TrendArticle(
                title=title,
                snippet=snippet[:300],
                source="Web",
                url=href,
                category="news",
            ))

    return articles[:max_results]


def _scrape_google_news(query: str, max_results: int = 5) -> list[TrendArticle]:
    """Scrape Google News search results."""
    url = f"https://www.google.com/search?q={quote_plus(query)}&tbm=nws&num={max_results}"
    html = _fetch(url, "google.com")
    if not html:
        return []

    tree = HTMLParser(html)
    articles = []

    for node in tree.css("div.SoaBEf, div.xuvV6b, div.MjjYud"):
        title_el = node.css_first("div.MBeuO, div.n0jPhd, h3")
        snippet_el = node.css_first("div.GI74Re, div.s3v9rd, span.aCOpRe")
        link_el = node.css_first("a[href]")
        source_el = node.css_first("div.OSrXXb, span.WF4CUc, div.CEMjEf")

        title = title_el.text(strip=True) if title_el else ""
        snippet = snippet_el.text(strip=True) if snippet_el else ""
        source = source_el.text(strip=True) if source_el else "Google News"
        href = link_el.attributes.get("href", "") if link_el else ""

        if title and len(title) > 10:
            articles.append(TrendArticle(
                title=title,
                snippet=snippet[:300],
                source=source,
                url=href,
                category="news",
            ))

    return articles[:max_results]


def _scrape_reddit(subreddit: str, query: str, max_results: int = 5) -> list[TrendArticle]:
    """Scrape Reddit search results via old.reddit.com."""
    url = f"https://old.reddit.com/r/{subreddit}/search?q={quote_plus(query)}&sort=relevance&t=year&restrict_sr=on"
    html = _fetch(url, "reddit.com")
    if not html:
        return []

    tree = HTMLParser(html)
    articles = []

    for node in tree.css("div.search-result"):
        title_el = node.css_first("a.search-title")
        snippet_el = node.css_first("span.search-result-body")

        title = title_el.text(strip=True) if title_el else ""
        snippet = snippet_el.text(strip=True) if snippet_el else ""
        href = title_el.attributes.get("href", "") if title_el else ""
        if href and not href.startswith("http"):
            href = f"https://old.reddit.com{href}"

        if title and len(title) > 5:
            articles.append(TrendArticle(
                title=title,
                snippet=snippet[:300],
                source=f"r/{subreddit}",
                url=href,
                category="social",
            ))

    return articles[:max_results]


def _scrape_the_verge(query: str, max_results: int = 5) -> list[TrendArticle]:
    """Scrape The Verge search results."""
    url = f"https://www.theverge.com/search?q={quote_plus(query)}"
    html = _fetch(url, "theverge.com")
    if not html:
        return []

    tree = HTMLParser(html)
    articles = []

    for node in tree.css("div.flex, article, li.duet--search--result"):
        title_el = node.css_first("a h2, h2 a, h3 a, a.font-bold, a[data-analytics-link]")
        snippet_el = node.css_first("p, div.leading-relaxed")

        title = title_el.text(strip=True) if title_el else ""
        snippet = snippet_el.text(strip=True) if snippet_el else ""

        href = ""
        if title_el:
            link = title_el if title_el.tag == "a" else title_el.parent
            if link and link.tag == "a":
                href = link.attributes.get("href", "")
            else:
                link = node.css_first("a[href]")
                href = link.attributes.get("href", "") if link else ""

        if href and not href.startswith("http"):
            href = f"https://www.theverge.com{href}"

        if title and len(title) > 10:
            articles.append(TrendArticle(
                title=title,
                snippet=snippet[:300],
                source="The Verge",
                url=href,
                category="news",
            ))

    return articles[:max_results]


def _scrape_verge_recent(max_results: int = 8) -> list[TrendArticle]:
    """Scrape recent The Verge tech articles from category pages."""
    articles = []
    for path in ["/tech", "/reviews"]:
        url = f"https://www.theverge.com{path}"
        html = _fetch(url, "theverge.com")
        if not html:
            continue

        tree = HTMLParser(html)
        for node in tree.css("a[href*='/20']"):
            h2 = node.css_first("h2, h3, span")
            if not h2:
                continue
            title = h2.text(strip=True)
            href = node.attributes.get("href", "")
            if href and not href.startswith("http"):
                href = f"https://www.theverge.com{href}"

            p = node.css_first("p")
            snippet = p.text(strip=True) if p else ""

            if title and len(title) > 15:
                articles.append(TrendArticle(
                    title=title,
                    snippet=snippet[:300],
                    source="The Verge",
                    url=href,
                    category="news",
                ))

    return articles[:max_results]


def _scrape_wired(query: str, max_results: int = 5) -> list[TrendArticle]:
    """Scrape Wired search results."""
    url = f"https://www.wired.com/search/?q={quote_plus(query)}&sort=score"
    html = _fetch(url, "wired.com")
    if not html:
        return []

    tree = HTMLParser(html)
    articles = []

    for node in tree.css("li[class*='summary-item'], div[class*='SummaryItem']"):
        title_el = node.css_first("h2 a, h3 a, a[class*='summary-item']")
        snippet_el = node.css_first("p[class*='description'], div[class*='dek']")

        title = title_el.text(strip=True) if title_el else ""
        snippet = snippet_el.text(strip=True) if snippet_el else ""
        href = ""
        if title_el and title_el.tag == "a":
            href = title_el.attributes.get("href", "")
        elif title_el:
            link = title_el.parent if title_el.parent and title_el.parent.tag == "a" else node.css_first("a[href]")
            href = link.attributes.get("href", "") if link else ""
        if href and not href.startswith("http"):
            href = f"https://www.wired.com{href}"

        if title and len(title) > 10:
            articles.append(TrendArticle(
                title=title,
                snippet=snippet[:300],
                source="Wired",
                url=href,
                category="review",
            ))

    return articles[:max_results]


def _scrape_cnet(query: str, max_results: int = 5) -> list[TrendArticle]:
    """Scrape CNET search results."""
    url = f"https://www.cnet.com/search/?query={quote_plus(query)}"
    html = _fetch(url, "cnet.com")
    if not html:
        return []

    tree = HTMLParser(html)
    articles = []

    for node in tree.css("div.searchResult, article, li[class*='item']"):
        title_el = node.css_first("h3 a, h2 a, a.title, a[data-type]")
        snippet_el = node.css_first("p, div.dek, span.description")

        title = title_el.text(strip=True) if title_el else ""
        snippet = snippet_el.text(strip=True) if snippet_el else ""
        href = ""
        if title_el and title_el.tag == "a":
            href = title_el.attributes.get("href", "")
        if href and not href.startswith("http"):
            href = f"https://www.cnet.com{href}"

        if title and len(title) > 10:
            articles.append(TrendArticle(
                title=title,
                snippet=snippet[:300],
                source="CNET",
                url=href,
                category="review",
            ))

    return articles[:max_results]


def _scrape_techradar(query: str, max_results: int = 5) -> list[TrendArticle]:
    """Scrape TechRadar search results."""
    url = f"https://www.techradar.com/search?searchTerm={quote_plus(query)}"
    html = _fetch(url, "techradar.com")
    if not html:
        return []

    tree = HTMLParser(html)
    articles = []

    for node in tree.css("div.listingResult, article.listing__item, div.search-result"):
        title_el = node.css_first("h3 a, a.article-link, h3")
        snippet_el = node.css_first("p.synopsis, p.listing__description, p")

        title = title_el.text(strip=True) if title_el else ""
        snippet = snippet_el.text(strip=True) if snippet_el else ""
        href = ""
        if title_el and title_el.tag == "a":
            href = title_el.attributes.get("href", "")
        elif title_el:
            link = node.css_first("a[href]")
            href = link.attributes.get("href", "") if link else ""
        if href and not href.startswith("http"):
            href = f"https://www.techradar.com{href}"

        if title and len(title) > 10:
            articles.append(TrendArticle(
                title=title,
                snippet=snippet[:300],
                source="TechRadar",
                url=href,
                category="review",
            ))

    return articles[:max_results]


def _scrape_rtings(query: str, max_results: int = 5) -> list[TrendArticle]:
    """Scrape RTINGS search results for expert TV/headphone reviews."""
    url = f"https://www.rtings.com/search?query={quote_plus(query)}"
    html = _fetch(url, "rtings.com")
    if not html:
        return []

    tree = HTMLParser(html)
    articles = []

    for node in tree.css("a.search_result, div.search-result-item"):
        title_el = node.css_first("h3, .search_result_title, span")
        snippet_el = node.css_first("p, .search_result_description")

        title = title_el.text(strip=True) if title_el else node.text(strip=True)[:100]
        snippet = snippet_el.text(strip=True) if snippet_el else ""
        href = node.attributes.get("href", "") if node.tag == "a" else ""
        if href and not href.startswith("http"):
            href = f"https://www.rtings.com{href}"

        if title and len(title) > 5:
            articles.append(TrendArticle(
                title=title,
                snippet=snippet[:300],
                source="RTINGS",
                url=href,
                category="review",
            ))

    return articles[:max_results]


# ---- Analysis with Claude ----

def _analyze_with_claude(articles: list[TrendArticle], product_brands: list[str]) -> list[TrendInsight]:
    """Use Claude to extract structured trend insights from scraped articles."""
    import anthropic

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return _fallback_analysis(articles, product_brands)

    articles_text = "\n\n".join(
        f"[{a.source}] {a.title}\n{a.snippet}" for a in articles if a.title
    )

    if not articles_text.strip():
        return []

    brands_hint = ", ".join(product_brands[:20]) if product_brands else "Samsung, LG, Sony, TCL, Sharp, Xiaomi, PEAQ, CHIQ"

    prompt = f"""Analyze these tech articles and social media posts about electronics.
Extract the top trending products and the qualities driving their popularity.

Focus on these brands if mentioned: {brands_hint}

Articles:
{articles_text}

Return a JSON array of trending products. Each entry:
{{
  "product_name": "specific product name",
  "brand": "brand name",
  "category": "TV" or "Headphones" or "Audio" or "Appliance",
  "trend_score": 1-10 (how much buzz),
  "qualities": ["quality1", "quality2", ...],
  "sentiment": "positive" or "neutral" or "negative",
  "summary": "one sentence why it's trending"
}}

Return 5-10 products max. Only valid JSON array, no markdown."""

    try:
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text.strip()
        # Extract JSON from response
        match = re.search(r'\[.*\]', text, re.DOTALL)
        if match:
            data = json.loads(match.group())
            return [
                TrendInsight(
                    product_name=d.get("product_name", ""),
                    brand=d.get("brand", ""),
                    category=d.get("category", ""),
                    trend_score=min(10, max(1, int(d.get("trend_score", 5)))),
                    qualities=d.get("qualities", []),
                    sentiment=d.get("sentiment", "positive"),
                    sources=[a.source for a in articles[:3]],
                    summary=d.get("summary", ""),
                )
                for d in data
                if d.get("product_name")
            ]
    except Exception:
        pass

    return _fallback_analysis(articles, product_brands)


def _fallback_analysis(articles: list[TrendArticle], product_brands: list[str]) -> list[TrendInsight]:
    """Simple keyword-based trend extraction when Claude is unavailable."""
    brand_mentions: dict[str, int] = {}
    quality_keywords = {
        "OLED": "OLED display",
        "QLED": "QLED technology",
        "Mini LED": "Mini LED backlight",
        "4K": "4K resolution",
        "8K": "8K resolution",
        "HDR": "HDR support",
        "Dolby": "Dolby audio/vision",
        "noise cancel": "Noise cancellation",
        "ANC": "Active noise cancellation",
        "battery life": "Long battery life",
        "smart": "Smart features",
        "gaming": "Gaming performance",
        "120Hz": "120Hz refresh rate",
        "price": "Competitive pricing",
    }

    for a in articles:
        text = f"{a.title} {a.snippet}".lower()
        for brand in product_brands:
            if brand.lower() in text:
                brand_mentions[brand] = brand_mentions.get(brand, 0) + 1

    insights = []
    for brand, count in sorted(brand_mentions.items(), key=lambda x: -x[1])[:6]:
        qualities = []
        for kw, qual in quality_keywords.items():
            for a in articles:
                if kw.lower() in f"{a.title} {a.snippet}".lower() and brand.lower() in f"{a.title} {a.snippet}".lower():
                    qualities.append(qual)
                    break
        if not qualities:
            qualities = ["Popular in reviews"]

        insights.append(TrendInsight(
            product_name=f"{brand} (trending)",
            brand=brand,
            category="Electronics",
            trend_score=min(10, count * 2),
            qualities=qualities[:4],
            sentiment="positive",
            sources=[a.source for a in articles[:2]],
            summary=f"{brand} mentioned in {count} recent articles/posts",
        ))

    return insights


# ---- Main Entry Point ----

def scrape_trends(brands: list[str] | None = None) -> dict:
    """Scrape trends from multiple sources and return analyzed insights."""
    from rich.console import Console
    console = Console()

    all_articles: list[TrendArticle] = []
    sources_used: list[str] = []

    # DuckDuckGo news search (most reliable)
    console.print("[dim]Scraping DuckDuckGo News...[/]")
    for q in ["best TV 2025 2026 review", "best headphones earbuds 2025 2026", "trending electronics OLED QLED"]:
        articles = _scrape_duckduckgo_news(q, max_results=5)
        all_articles.extend(articles)
        console.print(f"  [dim]{q}: {len(articles)} results[/]")
    if any(a.source == "Web" for a in all_articles):
        sources_used.append("DuckDuckGo")

    # The Verge
    console.print("[dim]Scraping The Verge...[/]")
    for q in ["best TV 2025", "best headphones 2025", "Samsung LG Sony"]:
        articles = _scrape_the_verge(q, max_results=4)
        all_articles.extend(articles)
        console.print(f"  [dim]The Verge search: {len(articles)} articles[/]")
    recent = _scrape_verge_recent(max_results=6)
    all_articles.extend(recent)
    console.print(f"  [dim]The Verge recent: {len(recent)} articles[/]")
    if any(a.source == "The Verge" for a in all_articles):
        sources_used.append("The Verge")

    # Wired
    console.print("[dim]Scraping Wired...[/]")
    for q in ["best TV 2025", "best headphones 2025"]:
        articles = _scrape_wired(q, max_results=4)
        all_articles.extend(articles)
        console.print(f"  [dim]Wired: {len(articles)} articles[/]")
    if any(a.source == "Wired" for a in all_articles):
        sources_used.append("Wired")

    # CNET
    console.print("[dim]Scraping CNET...[/]")
    for q in ["best TV 2025", "best wireless earbuds"]:
        articles = _scrape_cnet(q, max_results=4)
        all_articles.extend(articles)
        console.print(f"  [dim]CNET: {len(articles)} articles[/]")
    if any(a.source == "CNET" for a in all_articles):
        sources_used.append("CNET")

    # Google News
    console.print("[dim]Scraping Google News...[/]")
    for q in TECH_QUERIES[:3]:
        articles = _scrape_google_news(q, max_results=3)
        all_articles.extend(articles)
        console.print(f"  [dim]{q}: {len(articles)} articles[/]")
    if any(a.category == "news" and a.source not in ("Web", "The Verge", "Wired", "CNET") for a in all_articles):
        sources_used.append("Google News")

    # Reddit
    console.print("[dim]Scraping Reddit...[/]")
    for sub, q in REDDIT_QUERIES[:3]:
        articles = _scrape_reddit(sub, q, max_results=3)
        all_articles.extend(articles)
        console.print(f"  [dim]r/{sub}: {len(articles)} posts[/]")
    if any(a.category == "social" for a in all_articles):
        sources_used.append("Reddit")

    # TechRadar
    console.print("[dim]Scraping TechRadar...[/]")
    for q in ["best TV 2025", "best headphones 2025"]:
        articles = _scrape_techradar(q, max_results=3)
        all_articles.extend(articles)
        console.print(f"  [dim]TechRadar: {len(articles)} articles[/]")
    if any(a.source == "TechRadar" for a in all_articles):
        sources_used.append("TechRadar")

    # RTINGS
    console.print("[dim]Scraping RTINGS...[/]")
    for q in ["best TV", "best headphones"]:
        articles = _scrape_rtings(q, max_results=3)
        all_articles.extend(articles)
        console.print(f"  [dim]RTINGS: {len(articles)} articles[/]")
    if any(a.source == "RTINGS" for a in all_articles):
        sources_used.append("RTINGS")

    console.print(f"[bold]Total articles scraped: {len(all_articles)} from {len(sources_used)} sources[/]")

    # Deduplicate by title
    seen_titles: set[str] = set()
    unique_articles = []
    for a in all_articles:
        key = a.title.lower().strip()
        if key not in seen_titles:
            seen_titles.add(key)
            unique_articles.append(a)

    product_brands = brands or ["Samsung", "LG", "Sony", "TCL", "Sharp", "Xiaomi", "PEAQ", "CHIQ", "JBL", "Bose", "Sennheiser"]

    console.print("[dim]Analyzing trends with Claude...[/]")
    insights = _analyze_with_claude(unique_articles, product_brands)
    console.print(f"[bold green]Found {len(insights)} trending products[/]")

    return {
        "insights": [asdict(i) for i in insights],
        "articles": [asdict(a) for a in unique_articles[:25]],
        "total_articles": len(unique_articles),
        "sources_scraped": sources_used or ["DuckDuckGo", "The Verge", "Wired", "CNET", "Reddit", "TechRadar", "RTINGS"],
    }