from pydantic import BaseModel


class RecipeStats(BaseModel):
    """Resumen del historial del usuario autenticado."""

    total: int
    rated: int
    average_stars: float | None  # None si todavia no ha calificado ninguna receta
    by_difficulty: dict[str, int]
