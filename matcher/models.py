"""Data models for product matching."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Product:
    reference: str
    name: str
    brand: str = ""
    category: str = ""
    price_eur: float | None = None
    ean: str | None = None
    url: str | None = None
    image_url: str | None = None
    retailer: str | None = None
    specifications: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, d: dict) -> Product:
        return cls(
            reference=d.get("reference", ""),
            name=d.get("name", ""),
            brand=d.get("brand", ""),
            category=d.get("category", ""),
            price_eur=d.get("price_eur"),
            ean=d.get("ean"),
            url=d.get("url"),
            image_url=d.get("image_url"),
            retailer=d.get("retailer"),
            specifications=d.get("specifications", {}),
        )


@dataclass
class Match:
    source_reference: str
    target_reference: str
    target_name: str = ""
    target_retailer: str = ""
    target_url: str = ""
    target_price: float | None = None
    confidence: float = 1.0
    method: str = ""  # ean, fuzzy, model_number, claude, scrape


@dataclass
class SubmissionEntry:
    source_reference: str
    competitors: list[dict] = field(default_factory=list)

    def add_match(self, match: Match):
        self.competitors.append({
            "reference": match.target_reference,
            "competitor_retailer": match.target_retailer,
            "competitor_product_name": match.target_name,
            "competitor_url": match.target_url,
            "competitor_price": match.target_price,
        })

    def to_dict(self) -> dict:
        return {
            "source_reference": self.source_reference,
            "competitors": self.competitors,
        }
