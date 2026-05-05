"""
Профиль пользователя и его предпочтения.
"""
from pydantic import BaseModel, Field


class UserProfile(BaseModel):
    user_id: int
    gender: str | None = None
    style: str | None = None
    budget: str | None = None
    preferred_colors: list[str] = Field(default_factory=list)
    preferred_styles: list[str] = Field(default_factory=list)
    disliked_items: list[str] = Field(default_factory=list)
    key_items: list[str] = Field(default_factory=list)
