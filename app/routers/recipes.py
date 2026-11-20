from typing import Literal

from fastapi import APIRouter, Body, HTTPException, Query, Response, status
from sqlalchemy import and_, func, select
from sqlalchemy.orm import selectinload

from app.deps import CurrentUser, DbSession
from app.models.ingredient import Ingredient
from app.models.rating import Rating
from app.models.recipe import Recipe
from app.schemas.recipe import Difficulty, GenerateOptions, RatingCreate, RecipeOut
from app.schemas.stats import RecipeStats
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
async def generate_recipe(db: DbSession, user: CurrentUser, options: GenerateOptions | None = Body(None)):
    """Genera una receta con el inventario actual del usuario y la guarda en su historial.

    El cuerpo es opcional: sin él se genera una receta sin preferencias.
    """
    ingredients = db.scalars(select(Ingredient).where(Ingredient.user_id == user.id)).all()
    if not ingredients:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Agrega al menos un ingrediente a tu inventario")

    items = [{"name": i.name, "quantity": i.quantity, "unit": i.unit} for i in ingredients]
    try:
        content = await llm_service.generate_recipe(items, options)
    except llm_service.LLMTimeoutError as exc:
        raise HTTPException(
            status.HTTP_504_GATEWAY_TIMEOUT, "El generador de recetas tardó demasiado. Intenta de nuevo"
        ) from exc
    except llm_service.LLMBusyError as exc:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "El generador de recetas está saturado. Intenta de nuevo en un minuto",
            headers={"Retry-After": "60"},
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


def _escape_like(text: str) -> str:
    """Evita que % y _ escritos por el usuario actúen como comodines en ILIKE."""
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


@router.get("", response_model=list[RecipeOut])
def list_recipes(
    db: DbSession,
    user: CurrentUser,
    response: Response,
    q: str | None = Query(None, min_length=1, max_length=100, description="Buscar por nombre del plato"),
    difficulty: Difficulty | None = Query(None, description="Fácil, Media o Difícil"),
    min_rating: int | None = Query(None, ge=1, le=5, description="Solo recetas con al menos estas estrellas"),
    sort: Literal["recent", "oldest", "rating"] = Query(
        "recent", description="recent: más nuevas primero; oldest: más antiguas primero; rating: mejor calificadas"
    ),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """Historial del usuario con búsqueda, filtros y paginación.

    El total de recetas que cumplen los filtros (sin paginar) va en la cabecera X-Total-Count.
    """
    my_rating = and_(Rating.recipe_id == Recipe.id, Rating.user_id == user.id)
    stmt = select(Recipe).outerjoin(Rating, my_rating).where(Recipe.user_id == user.id)
    if q:
        stmt = stmt.where(Recipe.name.ilike(f"%{_escape_like(q.strip())}%", escape="\\"))
    if difficulty:
        stmt = stmt.where(Recipe.difficulty == difficulty)
    if min_rating:
        stmt = stmt.where(Rating.stars >= min_rating)

    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    response.headers["X-Total-Count"] = str(total)

    if sort == "oldest":
        order = [Recipe.created_at.asc(), Recipe.id.asc()]
    elif sort == "rating":
        order = [func.coalesce(Rating.stars, 0).desc(), Recipe.created_at.desc(), Recipe.id.desc()]
    else:
        order = [Recipe.created_at.desc(), Recipe.id.desc()]
    # selectinload trae todas las calificaciones en una sola consulta (evita N+1 en _to_out).
    stmt = stmt.options(selectinload(Recipe.ratings))
    stmt = stmt.order_by(*order).limit(limit).offset(offset)
    return [_to_out(r, user.id) for r in db.scalars(stmt).all()]


# Debe declararse antes de "/{recipe_id}" para que "stats" no se interprete como un id.
@router.get("/stats", response_model=RecipeStats)
def recipe_stats(db: DbSession, user: CurrentUser):
    total = db.scalar(select(func.count(Recipe.id)).where(Recipe.user_id == user.id))
    rated, average = db.execute(
        select(func.count(Rating.id), func.avg(Rating.stars))
        .join(Recipe, Recipe.id == Rating.recipe_id)
        .where(Rating.user_id == user.id, Recipe.user_id == user.id)
    ).one()
    by_difficulty = dict(
        db.execute(
            select(Recipe.difficulty, func.count(Recipe.id))
            .where(Recipe.user_id == user.id)
            .group_by(Recipe.difficulty)
        ).all()
    )
    return RecipeStats(
        total=total,
        rated=rated,
        average_stars=round(float(average), 2) if average is not None else None,
        by_difficulty=by_difficulty,
    )


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


@router.delete("/{recipe_id}/rating", response_model=RecipeOut)
def remove_rating(recipe_id: int, db: DbSession, user: CurrentUser):
    """Quita la calificación del usuario; si no existía, no hace nada."""
    recipe = _get_owned(db, user, recipe_id)
    rating = next((r for r in recipe.ratings if r.user_id == user.id), None)
    if rating is not None:
        db.delete(rating)
        db.commit()
        db.refresh(recipe)
    return _to_out(recipe, user.id)


@router.delete("/{recipe_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_recipe(recipe_id: int, db: DbSession, user: CurrentUser):
    db.delete(_get_owned(db, user, recipe_id))
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
