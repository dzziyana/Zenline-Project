"""Data models for product matching."""

from __future__ import annotations

from dataclasses import dataclass, field


BRAND_MAP = {
    # TV & Audio
    "samsung electronics gmbh": "Samsung",
    "samsung": "Samsung",
    "imtron gmbh": "PEAQ",
    "peaq": "PEAQ",
    "tcl": "TCL",
    "sharp": "Sharp",
    "xiaomi": "Xiaomi",
    "changhong": "CHIQ",
    "chiq": "CHIQ",
    "lg electronics": "LG",
    "lg": "LG",
    "sony": "Sony",
    "philips": "Philips",
    "hisense": "Hisense",
    "panasonic": "Panasonic",
    "jbl": "JBL",
    "sonos": "Sonos",
    "bose": "Bose",
    "sonero": "sonero",
    "deleyCON": "deleyCON",
    "deleycon": "deleyCON",
    "goobay": "Goobay",
    "ancable": "Ancable",
    "hama": "Hama",
    "dyon": "DYON",
    "telefunken": "TELEFUNKEN",
    "thomson": "Thomson",
    "grundig": "GRUNDIG",
    "jvc": "JVC",
    "kiano": "Kiano",
    "medion": "MEDION",
    "toshiba": "Toshiba",
    "soundcore": "soundcore",
    "strong": "STRONG",
    "cello": "Cello",
    # Small Appliances
    "gastroback": "GASTROBACK",
    "tefal": "Tefal",
    "clatronic": "Clatronic",
    "kenwood": "Kenwood",
    "beurer": "Beurer",
    "remington": "REMINGTON",
    "koenic": "KOENIC",
    "severin elektrogeräte gmbh": "SEVERIN",
    "severin": "SEVERIN",
    "rommelsbacher": "Rommelsbacher",
    "silva homeline": "SILVA",
    "silva-homeline": "SILVA",
    "silva": "SILVA",
    "wmf": "WMF",
    "braun": "Braun",
    "oral-b": "Oral-B",
    "meberg": "meberg",
    "gourmetmaxx": "GOURMETmaxx",
    "jonr": "JONR",
    "mova": "Mova",
    "stanew": "Stanew",
    "amazon basics": "Amazon Basics",
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

        # Extract brand - try explicit field first, then name, then specs
        brand = d.get("brand") or ""
        if brand:
            brand = _normalize_brand(brand)

        # Try to infer from product name (more reliable than specs like Hersteller
        # which can be a parent company e.g. "Imtron GmbH" for both KOENIC and PEAQ)
        if not brand:
            name_lower = d.get("name", "").lower()
            # Only match brand at start of name or as standalone word (not in descriptions
            # like "Samsung Tizen OS" when the product is actually a DYON TV)
            for key, val in BRAND_MAP.items():
                if name_lower.startswith(key):
                    brand = val
                    break
            # Second pass: match brand as standalone word but NOT after prepositions
            # like "mit", "für", "with", "for" which indicate compatibility, not brand
            if not brand:
                import re as _re
                for key, val in BRAND_MAP.items():
                    # Match " brand " but not after common prepositions
                    pattern = rf'(?<!\bmit )(?<!\bfür )(?<!\bfor )(?<!\bwith )\b{_re.escape(key)}\b'
                    m = _re.search(pattern, name_lower)
                    if m and m.start() < 30:  # brand should appear early in the name
                        brand = val
                        break

        # Fall back to specs fields
        if not brand:
            brand = specs.get("Marke") or specs.get("Hersteller") or specs.get("Brand") or ""
            brand = _normalize_brand(brand)

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
