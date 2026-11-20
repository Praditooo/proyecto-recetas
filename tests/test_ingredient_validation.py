import pytest
from pydantic import ValidationError

from app.schemas.ingredient import ALLOWED_UNITS, IngredientBase


def test_valid_ingredient_is_normalized():
    ingredient = IngredientBase(name="  Tomate   rojo ", quantity=2, unit=" KG ")
    assert ingredient.name == "Tomate rojo"
    assert ingredient.unit == "kg"


@pytest.mark.parametrize("quantity", [0, -1, -0.5])
def test_rejects_non_positive_quantity(quantity):
    with pytest.raises(ValidationError):
        IngredientBase(name="arroz", quantity=quantity, unit="g")


def test_rejects_blank_name():
    with pytest.raises(ValidationError):
        IngredientBase(name="   ", quantity=1, unit="g")


@pytest.mark.parametrize("unit", ALLOWED_UNITS)
def test_accepts_all_allowed_units(unit):
    ingredient = IngredientBase(name="test", quantity=1, unit=unit)
    assert ingredient.unit == unit


def test_rejects_invalid_unit():
    with pytest.raises(ValidationError, match="Unidad no permitida"):
        IngredientBase(name="arroz", quantity=1, unit="barril")
