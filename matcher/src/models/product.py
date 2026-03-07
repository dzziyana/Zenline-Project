from pydantic import BaseModel


class SourceProduct(BaseModel):
    reference: str
    name: str
    brand: str | None = None
    ean: str | None = None
    category: str | None = None
    price: float | None = None
    attributes: dict = {}


class TargetProduct(BaseModel):
    reference: str
    name: str
    brand: str | None = None
    ean: str | None = None
    retailer: str | None = None
    url: str | None = None
    price: float | None = None
    category: str | None = None
    attributes: dict = {}


class CompetitorMatch(BaseModel):
    reference: str
    competitor_retailer: str | None = None
    competitor_product_name: str | None = None
    competitor_url: str | None = None
    competitor_price: float | None = None
    confidence: float = 0.0
    match_method: str = ""


class SourceProductSubmission(BaseModel):
    source_reference: str
    competitors: list[CompetitorMatch] = []
