import hashlib

from bs4 import BeautifulSoup

from src.models.product import TargetProduct
from src.scraping.base_scraper import BaseScraper


class Electronic4youScraper(BaseScraper):
    retailer_name = "electronic4you.at"
    base_url = "https://www.electronic4you.at"

    async def search_by_ean(self, ean: str) -> list[TargetProduct]:
        url = f"{self.base_url}/catalogsearch/result/?q={ean}"
        return await self._parse_search_results(url)

    async def search_by_name(self, name: str) -> list[TargetProduct]:
        query = name.replace(" ", "+")
        url = f"{self.base_url}/catalogsearch/result/?q={query}"
        return await self._parse_search_results(url)

    async def _parse_search_results(self, url: str) -> list[TargetProduct]:
        try:
            response = await self._get(url)
            if response.status_code != 200:
                return []

            soup = BeautifulSoup(response.text, "lxml")
            products = []

            # TODO: Update selectors after inspecting live site structure
            for item in soup.select(".product-item, .item, [data-product-id]"):
                name_el = item.select_one(".product-item-link, .product-name, h2, h3")
                price_el = item.select_one(".price, .product-price, [data-price-amount]")
                link_el = item.select_one("a[href]")

                if not name_el:
                    continue

                product_name = name_el.get_text(strip=True)
                product_url = ""
                if link_el:
                    href = link_el.get("href", "")
                    product_url = (
                        href
                        if href.startswith("http")
                        else f"{self.base_url}{href}"
                    )

                price = None
                if price_el:
                    price_text = price_el.get_text(strip=True)
                    price = _parse_price(price_text)

                ref = _generate_reference(product_url or product_name)
                products.append(
                    TargetProduct(
                        reference=ref,
                        name=product_name,
                        retailer=self.retailer_name,
                        url=product_url,
                        price=price,
                    )
                )

            return products
        except Exception:
            return []


def _parse_price(text: str) -> float | None:
    try:
        cleaned = (
            text.replace("€", "")
            .replace("\xa0", "")
            .replace(".", "")
            .replace(",", ".")
            .strip()
        )
        return float(cleaned)
    except ValueError:
        return None


def _generate_reference(identifier: str) -> str:
    h = hashlib.md5(identifier.encode()).hexdigest()[:8].upper()
    return f"P_{h}"
