"""Web scraping for hidden retailers.

Uses three strategies:
1. expert.at - Parse __NUXT__ SSR data from search results
2. electronic4you.at - curl_cffi with browser impersonation + HTML parsing
3. geizhals.at - Price aggregator fallback for e-tec.at and cyberport.at
   (both sites block automated requests)
"""

from __future__ import annotations

import asyncio
import json
import re
import time
from urllib.parse import quote_plus

from curl_cffi import requests as cffi_requests
from selectolax.parser import HTMLParser

from .models import Match, Product

MIN_DELAY = 1.5  # seconds between requests to same domain
_last_request: dict[str, float] = {}


def _rate_limit_sync(domain: str):
    """Ensure we don't hit the same domain too fast."""
    now = time.time()
    last = _last_request.get(domain, 0)
    wait = MIN_DELAY - (now - last)
    if wait > 0:
        time.sleep(wait)
    _last_request[domain] = time.time()


def _parse_price(text: str) -> float | None:
    """Parse a price string like 'EUR 1.299,00' or '1299.00' into a float."""
    text = text.replace("EUR", "").replace("€", "").replace("\xa0", "").replace(",-", ",00").replace(",\u2013", ",00").strip()
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


# ---------------------------------------------------------------------------
# expert.at - Nuxt.js SSR parsing
# ---------------------------------------------------------------------------

def _parse_expert_nuxt_values(values_raw: str) -> list:
    """Parse the NUXT function arguments into a list of values."""
    values = []
    i = 0
    length = len(values_raw)
    while i < length:
        c = values_raw[i]
        if c in ' \n\t':
            i += 1
            continue
        if c == ',':
            i += 1
            continue
        if c == '"':
            j = i + 1
            while j < length:
                if values_raw[j] == '\\':
                    j += 2
                elif values_raw[j] == '"':
                    break
                else:
                    j += 1
            values.append(values_raw[i + 1:j].replace('\\u002F', '/'))
            i = j + 1
        elif c in '0123456789.-':
            j = i
            while j < length and values_raw[j] not in ',)':
                j += 1
            val = values_raw[i:j].strip()
            try:
                values.append(float(val) if '.' in val else int(val))
            except ValueError:
                values.append(val)
            i = j
        elif values_raw[i:i + 4] == 'true':
            values.append(True)
            i += 4
        elif values_raw[i:i + 5] == 'false':
            values.append(False)
            i += 5
        elif values_raw[i:i + 4] == 'null':
            values.append(None)
            i += 4
        elif values_raw[i:i + 4] == 'void':
            j = i
            while j < length and values_raw[j] != ',':
                j += 1
            values.append(None)
            i = j
        else:
            j = i
            while j < length and values_raw[j] != ',':
                j += 1
            values.append(values_raw[i:j].strip())
            i = j
    return values


def _parse_expert_results(html: str) -> list[dict]:
    """Parse expert.at search results from __NUXT__ SSR data."""
    match = re.search(
        r'window\.__NUXT__\s*=\s*\(function\(([^)]*)\)\{return (.*)\}\((.*)\)\)',
        html, re.DOTALL,
    )
    if not match:
        return []

    params = match.group(1).split(',')
    template = match.group(2)
    values_raw = match.group(3)

    values = _parse_expert_nuxt_values(values_raw)
    var_map = {}
    for idx, p in enumerate(params):
        p = p.strip()
        if idx < len(values):
            var_map[p] = values[idx]

    results = []
    for m in re.finditer(
        r'\{id:"(\d+)",name:"([^"]+)",description:"([^"]*)".*?priceRegular:(\w+).*?path:"([^"]+)"\}',
        template,
    ):
        pid = m.group(1)
        name = m.group(2).replace('\\u002F', '/').replace('\\"', '"')
        desc = m.group(3).replace('\\u002F', '/').replace('\\"', '"')
        price_var = m.group(4)
        path = m.group(5).replace('\\u002F', '/')

        price = var_map.get(price_var, price_var)
        if isinstance(price, str):
            try:
                price = float(price)
            except ValueError:
                price = None

        full_name = f"{name} - {desc}" if desc else name
        results.append({
            'name': full_name,
            'url': f"https://www.expert.at{path}",
            'price': float(price) if price is not None else None,
            'retailer': 'Expert AT',
        })

    return results


def search_expert_at(query: str) -> list[dict]:
    """Search expert.at for products."""
    _rate_limit_sync('expert.at')
    search_url = f"https://www.expert.at/shop?q={quote_plus(query)}"
    try:
        r = cffi_requests.get(search_url, impersonate='chrome', timeout=15)
        if r.status_code == 200:
            return _parse_expert_results(r.text)
    except Exception:
        pass
    return []


# ---------------------------------------------------------------------------
# electronic4you.at - curl_cffi + HTML parsing
# ---------------------------------------------------------------------------

def _parse_electronic4you_results(html: str) -> list[dict]:
    """Parse electronic4you.at search results from HTML."""
    tree = HTMLParser(html)
    results = []
    for node in tree.css('li.item.flip-container'):
        name_el = node.css_first('a.product-image')
        price_el = node.css_first('.price')

        name = name_el.attributes.get('title', '') if name_el else ''
        url = name_el.attributes.get('href', '') if name_el else ''
        price_text = price_el.text(strip=True) if price_el else ''

        if name:
            results.append({
                'name': name,
                'url': url,
                'price': _parse_price(price_text) if price_text else None,
                'retailer': 'electronic4you.at',
            })
    return results


def search_electronic4you(query: str) -> list[dict]:
    """Search electronic4you.at for products."""
    _rate_limit_sync('electronic4you.at')
    search_url = f"https://www.electronic4you.at/catalogsearch/result/?q={quote_plus(query)}"
    try:
        r = cffi_requests.get(search_url, impersonate='chrome', timeout=15)
        if r.status_code == 200:
            return _parse_electronic4you_results(r.text)
    except Exception:
        pass
    return []


# ---------------------------------------------------------------------------
# geizhals.at - Price aggregator (covers e-tec.at, cyberport.at, and others)
# ---------------------------------------------------------------------------

def _parse_geizhals_results(html: str, target_retailers: dict[str, str] | None = None) -> list[dict]:
    """Parse geizhals.at product page for offers from target retailers."""
    if target_retailers is None:
        target_retailers = {
            'e-tec': 'E-Tec',
            'cyberport': 'Cyberport AT',
            'expert': 'Expert AT',
            'electronic4you': 'electronic4you.at',
        }

    tree = HTMLParser(html)
    results = []
    seen_retailers = set()

    # Get product name from page title
    title_el = tree.css_first('title')
    page_title = title_el.text() if title_el else ''
    # Clean title: "Samsung QE50Q7F ab EUR 401,91 (2026) | Preisvergleich..." -> "Samsung QE50Q7F"
    product_name = re.sub(r'\s*ab\s.*', '', page_title).strip()

    for offer in tree.css('.offer'):
        merchant_el = offer.css_first('.merchant__logo-caption')
        if not merchant_el:
            continue
        merchant = merchant_el.text(strip=True)

        for key, display_name in target_retailers.items():
            if key in merchant.lower() and display_name not in seen_retailers:
                price_el = offer.css_first('.gh_price')
                link_el = offer.css_first('.offer__clickout a, .offer__price-link')

                price_text = price_el.text(strip=True) if price_el else ''
                link = ''
                if link_el:
                    href = link_el.attributes.get('href', '')
                    if href:
                        link = href if href.startswith('http') else f'https://geizhals.at{href}'

                results.append({
                    'name': product_name,
                    'url': link,
                    'price': _parse_price(price_text) if price_text else None,
                    'retailer': display_name,
                })
                seen_retailers.add(display_name)
                break

    return results


def search_geizhals(query: str, only_retailers: list[str] | None = None) -> list[dict]:
    """Search geizhals.at and extract offers from target retailers."""
    _rate_limit_sync('geizhals.at')
    search_url = f"https://geizhals.at/?fs={quote_plus(query)}"
    try:
        r = cffi_requests.get(search_url, impersonate='chrome', timeout=15)
        if r.status_code == 200:
            target_retailers = None
            if only_retailers:
                all_retailers = {
                    'e-tec': 'E-Tec',
                    'cyberport': 'Cyberport AT',
                    'expert': 'Expert AT',
                    'electronic4you': 'electronic4you.at',
                }
                target_retailers = {k: v for k, v in all_retailers.items() if v in only_retailers}
            return _parse_geizhals_results(r.text, target_retailers)
    except Exception:
        pass
    return []


# ---------------------------------------------------------------------------
# Unified scraper interface
# ---------------------------------------------------------------------------

def _get_all_eans(source: Product) -> list[str]:
    """Extract all EAN/GTIN codes from a product."""
    eans = []
    if source.ean:
        eans.append(source.ean)
    if source.specifications:
        for key in ('GTIN', 'EAN-Code'):
            val = source.specifications.get(key)
            if val and val not in eans:
                eans.append(val)
    return eans


def _build_search_queries(source: Product) -> list[str]:
    """Build search queries in priority order: EAN first, then model/name."""
    queries = []

    # EAN/GTIN codes
    eans = _get_all_eans(source)
    queries.extend(eans)

    # Model number
    from .fuzzy_match import extract_model_number
    model = extract_model_number(source)
    if model and source.brand:
        queries.append(f"{source.brand} {model}")
    elif model:
        queries.append(model)

    # Shortened product name (first ~60 chars, remove noise)
    name = source.name
    # Remove common noise from product names
    name = re.sub(r'\s*\|.*$', '', name)
    name = re.sub(r'\s*online kaufen.*$', '', name, flags=re.IGNORECASE)
    name = re.sub(r'\s*\((?:\d+["\']|.*?cm)\)', '', name)
    short_name = name[:80].strip()
    if short_name and short_name not in queries:
        queries.append(short_name)

    return queries


def _is_relevant(source: Product, result: dict) -> bool:
    """Check if a scraped result is plausibly the same product as the source.

    Filters out obviously wrong results (e.g. a phone when searching for a TV).
    """
    from .fuzzy_match import extract_model_number

    src_model = extract_model_number(source)
    result_name = result['name'].upper()

    # If the source model number appears in the result, it's relevant
    if src_model and src_model.upper() in result_name:
        return True

    # If brand matches, check that result is the same product category and size
    if source.brand and source.brand.upper() in result_name:
        # Extract screen size from both
        src_size_m = re.search(r'(\d{2,3})\s*(?:Zoll|"|\'\')', source.name, re.IGNORECASE)
        # Also check specs for size
        if not src_size_m and source.specifications:
            diag = source.specifications.get('Bildschirmdiagonale (cm/Zoll)', '')
            src_size_m = re.search(r'(\d{2,3})\s*Zoll', diag)
        result_size_m = re.search(r'(\d{2,3})\s*(?:Zoll|"|\'\'|\\\"|cm)', result['name'], re.IGNORECASE)
        # Also try to extract size from patterns like "LED-TV 98\" or "65\"
        if not result_size_m:
            result_size_m = re.search(r'(\d{2,3})[\\\"]', result['name'])

        url = result.get('url', '').lower()
        is_tv_url = any(kw in url for kw in ['fernseher', 'tv-', '/tv/', 'fernseh', 'led-tv', 'qled', 'oled'])

        if src_size_m:
            src_size = int(src_size_m.group(1))
            # Source is a TV - result should also be a TV
            tv_keywords = ['TV', 'LED', 'QLED', 'OLED', 'LCD', 'FERNSEHER', 'SMART TV', 'UHD', 'FULL HD']
            is_tv_result = is_tv_url or any(kw in result_name for kw in tv_keywords)
            if not is_tv_result:
                return False
            # If result has a size, it should be close to source size
            if result_size_m:
                result_size = int(result_size_m.group(1))
                # Allow some tolerance (e.g. 32 vs 32, but not 32 vs 98)
                if abs(src_size - result_size) > 5:
                    return False
            return True
        # Non-TV source - just check brand match is sufficient
        return True

    # No brand or model match - not relevant
    return False


def scrape_product(source: Product) -> list[dict]:
    """Search all hidden retailers for a single source product.

    Returns list of dicts with keys: name, url, price, retailer, query_used.
    """
    queries = _build_search_queries(source)
    all_results = []
    retailers_found: dict[str, list[dict]] = {}

    for query in queries:
        # Expert AT - direct search
        if 'Expert AT' not in retailers_found:
            results = search_expert_at(query)
            relevant = [r for r in results if _is_relevant(source, r)]
            if relevant:
                retailers_found['Expert AT'] = relevant
                all_results.extend(relevant)

        # electronic4you.at - direct search
        if 'electronic4you.at' not in retailers_found:
            results = search_electronic4you(query)
            relevant = [r for r in results if _is_relevant(source, r)]
            if relevant:
                retailers_found['electronic4you.at'] = relevant
                all_results.extend(relevant)

        # Geizhals fallback for e-tec and cyberport (only search with EANs)
        missing = [r for r in ['E-Tec', 'Cyberport AT'] if r not in retailers_found]
        if missing and (query.isdigit() and len(query) >= 8):
            results = search_geizhals(query, only_retailers=missing)
            for r in results:
                if r['retailer'] not in retailers_found:
                    retailers_found[r['retailer']] = [r]
                    all_results.append(r)

        # Stop early if we found results from all retailers
        if len(retailers_found) >= 4:
            break

    # Tag results with the source reference for tracking
    for r in all_results:
        r['source_reference'] = source.reference

    return all_results


def scrape_all(sources: list[Product]) -> list[dict]:
    """Scrape all hidden retailers for all source products.

    Returns flat list of result dicts.
    """
    all_results = []
    for i, source in enumerate(sources):
        print(f"  Scraping [{i+1}/{len(sources)}] {source.name[:50]}...")
        results = scrape_product(source)
        print(f"    Found {len(results)} results from {len(set(r['retailer'] for r in results))} retailers")
        all_results.extend(results)
    return all_results


def results_to_matches(results: list[dict]) -> list[Match]:
    """Convert scraper results to Match objects."""
    matches = []
    for r in results:
        ref = f"SCRAPED_{r['retailer'].replace(' ', '_')}_{hash(r.get('url', r['name'])) % 10**8:08d}"
        matches.append(Match(
            source_reference=r['source_reference'],
            target_reference=ref,
            target_name=r['name'],
            target_retailer=r['retailer'],
            target_url=r.get('url', ''),
            target_price=r.get('price'),
            confidence=0.7,
            method='scrape',
        ))
    return matches
