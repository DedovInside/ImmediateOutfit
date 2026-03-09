"""
Pydantic-модель для outfit (образа) из JSON-базы.
"""
from pydantic import BaseModel


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

