from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import select

from app.deps import CurrentUser, DbSession
from app.models.ingredient import Ingredient
from app.models.rating import Rating
from app.models.recipe import Recipe
from app.schemas.recipe import RatingCreate, RecipeOut
from app.services import llm_service

router = APIRouter(prefix="/api/recipes", tags=["recetas"])


def _to_out(recipe: Recipe, user_id: int) -> RecipeOut:
    out = RecipeOut.model_validate(recipe)
    out.rating = next((r.stars for r in recipe.ratings if r.user_id == user_id), None)
    return out


def _get_owned(db: DbSession, user: CurrentUser, recipe_id: int) -> Recipe:
    recipe = db.get(Recipe, recipe_id)
    if recipe is None or recipe.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Receta no encontrada")
    return recipe


@router.post("/generate", response_model=RecipeOut, status_code=status.HTTP_201_CREATED)
async def generate_recipe(db: DbSession, user: CurrentUser):
    """Genera una receta con el inventario actual del usuario y la guarda en su historial."""
    ingredients = db.scalars(select(Ingredient).where(Ingredient.user_id == user.id)).all()
    if not ingredients:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Agrega al menos un ingrediente a tu inventario")

    items = [{"name": i.name, "quantity": i.quantity, "unit": i.unit} for i in ingredients]
    try:
        content = await llm_service.generate_recipe(items)
    except llm_service.LLMTimeoutError as exc:
        raise HTTPException(
            status.HTTP_504_GATEWAY_TIMEOUT, "El generador de recetas tardó demasiado. Intenta de nuevo"
        ) from exc
    except llm_service.LLMServiceError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"No se pudo generar la receta: {exc}") from exc

    recipe = Recipe(
        user_id=user.id,
        name=content.name,
        ingredients=[i.model_dump() for i in content.ingredients],
        steps=content.steps,
        estimated_minutes=content.estimated_minutes,
        difficulty=content.difficulty,
    )
    db.add(recipe)
    db.commit()
    db.refresh(recipe)
    return _to_out(recipe, user.id)


@router.get("", response_model=list[RecipeOut])
def list_recipes(db: DbSession, user: CurrentUser):
    stmt = select(Recipe).where(Recipe.user_id == user.id).order_by(Recipe.created_at.desc(), Recipe.id.desc())
    return [_to_out(r, user.id) for r in db.scalars(stmt).all()]


@router.get("/{recipe_id}", response_model=RecipeOut)
def get_recipe(recipe_id: int, db: DbSession, user: CurrentUser):
    return _to_out(_get_owned(db, user, recipe_id), user.id)


@router.post("/{recipe_id}/rating", response_model=RecipeOut)
def rate_recipe(recipe_id: int, data: RatingCreate, db: DbSession, user: CurrentUser):
    recipe = _get_owned(db, user, recipe_id)
    rating = next((r for r in recipe.ratings if r.user_id == user.id), None)
    if rating is None:
        db.add(Rating(user_id=user.id, recipe_id=recipe.id, stars=data.stars))
    else:
        rating.stars = data.stars
    db.commit()
    db.refresh(recipe)
    return _to_out(recipe, user.id)


@router.delete("/{recipe_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_recipe(recipe_id: int, db: DbSession, user: CurrentUser):
    db.delete(_get_owned(db, user, recipe_id))
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
