import pytest
from pydantic import ValidationError

from app.schemas.ingredient import IngredientBase


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
