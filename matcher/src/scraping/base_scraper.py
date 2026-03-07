import asyncio
from abc import ABC, abstractmethod

import httpx

from src.models.product import TargetProduct

DEFAULT_HEADERS = {
    "User-Agent": "ZenlineProductMatcher/1.0 (hackathon project)",
    "Accept": "text/html,application/xhtml+xml,application/json",
    "Accept-Language": "de-AT,de;q=0.9,en;q=0.8",
}

REQUEST_DELAY = 0.5  # seconds between requests


class BaseScraper(ABC):
    retailer_name: str
    base_url: str

    def __init__(self):
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                headers=DEFAULT_HEADERS,
                timeout=30.0,
                follow_redirects=True,
            )
        return self._client

    async def _get(self, url: str) -> httpx.Response:
        client = await self._get_client()
        await asyncio.sleep(REQUEST_DELAY)
        return await client.get(url)

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None

    @abstractmethod
    async def search_by_ean(self, ean: str) -> list[TargetProduct]:
        """Search the retailer website by EAN barcode."""
        ...

    @abstractmethod
    async def search_by_name(self, name: str) -> list[TargetProduct]:
        """Search the retailer website by product name."""
        ...

    async def search_product(
        self, ean: str | None, name: str
    ) -> list[TargetProduct]:
        """Search by EAN first, then fall back to name search."""
        results = []
        if ean:
            results = await self.search_by_ean(ean)
        if not results:
            results = await self.search_by_name(name)
        return results
