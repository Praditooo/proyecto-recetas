from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Difficulty = Literal["Fácil", "Media", "Difícil"]


class RecipeIngredient(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    quantity: float = Field(gt=0)
    unit: str = Field(min_length=1, max_length=20)


class RecipeContent(BaseModel):
    """Contrato JSON que el LLM debe devolver (se valida en llm_service)."""

    name: str = Field(min_length=1, max_length=200)
    ingredients: list[RecipeIngredient] = Field(min_length=1)
    steps: list[str] = Field(min_length=1)
    estimated_minutes: int = Field(gt=0, le=1440)
    difficulty: Difficulty

    @field_validator("steps")
    @classmethod
    def steps_not_blank(cls, steps: list[str]) -> list[str]:
        cleaned = [" ".join(step.split()) for step in steps]
        if any(not step for step in cleaned):
            raise ValueError("Ningún paso de la receta puede estar vacío")
        return cleaned

    @field_validator("ingredients")
    @classmethod
    def ingredients_not_repeated(cls, ingredients: list[RecipeIngredient]) -> list[RecipeIngredient]:
        names = [" ".join(i.name.split()).lower() for i in ingredients]
        if len(names) != len(set(names)):
            raise ValueError("La receta repite ingredientes")
        return ingredients


class RecipeOut(RecipeContent):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    rating: int | None = None  # calificación del usuario actual


class RatingCreate(BaseModel):
    stars: int = Field(ge=1, le=5)
