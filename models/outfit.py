"""
Pydantic-модель для outfit (образа) из JSON-базы.
"""
from pydantic import BaseModel
from pydantic import Field


class PurchaseLink(BaseModel):
    label: str
    article: str | None = None
    url: str | None = None


class OutfitReference(BaseModel):
    title: str
    description: str
    image_url: str | None = None


class Outfit(BaseModel):
    id: str
    name: str
    gender: list[str]          # "male", "female", или оба
    occasion: list[str]
    activity: list[str]
    priority: list[str]
    style: list[str]
    weather: list[str] = []
    items: dict[str, str]
    description: str
    tip: str
    budget_level: str = "medium"
    dress_code: list[str] = []
    season: list[str] = []
    why_it_fits: list[str] = []
    reference: OutfitReference | None = None
    purchase_links: list[PurchaseLink] = Field(default_factory=list)
    palette: list[str] = Field(default_factory=list)
    styling_notes: list[str] = Field(default_factory=list)
    source: str | None = None
