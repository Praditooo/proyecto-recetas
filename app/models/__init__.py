"""Importar todos los modelos aquí para que Base.metadata los conozca."""
from app.models.ingredient import Ingredient
from app.models.rating import Rating
from app.models.recipe import Recipe
from app.models.user import User

__all__ = ["Ingredient", "Rating", "Recipe", "User"]
