from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Response, status
from sqlalchemy import func, select

from app.deps import CurrentUser, DbSession
from app.models.ingredient import Ingredient
from app.schemas.ingredient import IngredientCreate, IngredientOut, IngredientUpdate, MAX_INGREDIENTS_PER_USER

router = APIRouter(prefix="/api/ingredients", tags=["ingredientes"])


def _get_owned(db: DbSession, user: CurrentUser, ingredient_id: int) -> Ingredient:
    ingredient = db.get(Ingredient, ingredient_id)
    if ingredient is None or ingredient.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ingrediente no encontrado")
    return ingredient


@router.get("/{ingredient_id}", response_model=IngredientOut)
def get_ingredient(ingredient_id: int, db: DbSession, user: CurrentUser):
    return _get_owned(db, user, ingredient_id)


@router.get("", response_model=list[IngredientOut])
def list_ingredients(
    db: DbSession,
    user: CurrentUser,
    q: Optional[str] = Query(None, min_length=1, max_length=100, description="Buscar ingredientes por nombre"),
):
    stmt = select(Ingredient).where(Ingredient.user_id == user.id)
    if q:
        stmt = stmt.where(Ingredient.name.ilike(f"%{q}%"))
    stmt = stmt.order_by(Ingredient.name)
    return db.scalars(stmt).all()


@router.post("", response_model=IngredientOut, status_code=status.HTTP_201_CREATED)
def create_ingredient(data: IngredientCreate, db: DbSession, user: CurrentUser):
    # Límite máximo de ingredientes por usuario
    total = db.scalar(select(func.count()).where(Ingredient.user_id == user.id))
    if total >= MAX_INGREDIENTS_PER_USER:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"No puedes tener más de {MAX_INGREDIENTS_PER_USER} ingredientes en el inventario",
        )
    # Fusión de duplicados: si ya existe un ingrediente con mismo nombre y unidad,
    # se suma la cantidad en lugar de crear uno nuevo.
    normalized_name = data.name.strip().lower()
    stmt = select(Ingredient).where(
        Ingredient.user_id == user.id,
        Ingredient.name.ilike(normalized_name),
        Ingredient.unit == data.unit,
    )
    existing = db.scalars(stmt).first()
    if existing:
        existing.quantity += data.quantity
        db.commit()
        db.refresh(existing)
        return existing

    ingredient = Ingredient(user_id=user.id, **data.model_dump())
    db.add(ingredient)
    db.commit()
    db.refresh(ingredient)
    return ingredient


@router.put("/{ingredient_id}", response_model=IngredientOut)
def update_ingredient(ingredient_id: int, data: IngredientUpdate, db: DbSession, user: CurrentUser):
    ingredient = _get_owned(db, user, ingredient_id)
    for field, value in data.model_dump().items():
        setattr(ingredient, field, value)
    db.commit()
    db.refresh(ingredient)
    return ingredient


@router.delete("/{ingredient_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ingredient(ingredient_id: int, db: DbSession, user: CurrentUser):
    db.delete(_get_owned(db, user, ingredient_id))
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
