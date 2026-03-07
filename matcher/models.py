"""Data models for product matching."""

from __future__ import annotations

from dataclasses import dataclass, field


BRAND_MAP = {
    "samsung electronics gmbh": "Samsung",
    "samsung": "Samsung",
    "imtron gmbh": "PEAQ",
    "tcl": "TCL",
    "sharp": "Sharp",
    "xiaomi": "Xiaomi",
    "changhong": "CHIQ",
    "lg electronics": "LG",
    "lg": "LG",
    "sony": "Sony",
    "philips": "Philips",
    "hisense": "Hisense",
    "panasonic": "Panasonic",
    "jbl": "JBL",
    "sonos": "Sonos",
    "bose": "Bose",
}


def _normalize_brand(brand: str) -> str:
    brand_lower = brand.strip().lower()
    for key, val in BRAND_MAP.items():
        if key in brand_lower:
            return val
    return brand.strip()


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
        specs = d.get("specifications") or {}

        # Extract EAN from multiple possible fields
        ean = d.get("ean")
        if not ean:
            ean = specs.get("GTIN") or specs.get("EAN-Code") or specs.get("EAN")

        # Extract brand from multiple possible fields
        brand = d.get("brand") or ""
        if not brand:
            brand = specs.get("Hersteller") or specs.get("Marke") or specs.get("Brand") or ""
        brand = _normalize_brand(brand)

        # If brand still empty, try to infer from product name
        if not brand:
            name_lower = d.get("name", "").lower()
            for key, val in BRAND_MAP.items():
                if name_lower.startswith(key) or f" {key} " in name_lower:
                    brand = val
                    break

        return cls(
            reference=d.get("reference", ""),
            name=d.get("name", ""),
            brand=brand,
            category=d.get("category", ""),
            price_eur=d.get("price_eur"),
            ean=ean,
            url=d.get("url"),
            image_url=d.get("image_url"),
            retailer=d.get("retailer"),
            specifications=specs,
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
