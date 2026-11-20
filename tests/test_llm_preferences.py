"""Pruebas de las preferencias de generación (dieta, tiempo máximo y porciones)."""
import pytest
from pydantic import ValidationError

from app.schemas.recipe import GenerateOptions, RecipeContent, RecipeIngredient
from app.services import llm_service

INVENTORY = [{"name": "arroz", "quantity": 500, "unit": "g"}]


def _recipe(minutes: int = 25) -> RecipeContent:
    return RecipeContent(
        name="Arroz blanco",
        ingredients=[RecipeIngredient(name="arroz", quantity=200, unit="g")],
        steps=["Cocina el arroz"],
        estimated_minutes=minutes,
        difficulty="Fácil",
    )


def test_prompt_without_options_has_no_preferences():
    user_message = llm_service.build_messages(INVENTORY)[1]["content"]
    assert "Preferencias" not in user_message


def test_prompt_includes_every_chosen_preference():
    options = GenerateOptions(diet="vegana", max_minutes=30, servings=4)
    user_message = llm_service.build_messages(INVENTORY, options)[1]["content"]
    assert "La receta debe ser vegana." in user_message
    assert "no debe superar 30 minutos" in user_message
    assert "para 4 porciones" in user_message


def test_prompt_uses_singular_for_one_serving():
    user_message = llm_service.build_messages(INVENTORY, GenerateOptions(servings=1))[1]["content"]
    assert "para 1 porción." in user_message


@pytest.mark.parametrize("bad", [{"diet": "carnívora"}, {"max_minutes": 2}, {"servings": 0}, {"servings": 50}])
def test_options_reject_invalid_values(bad):
    with pytest.raises(ValidationError):
        GenerateOptions(**bad)


def test_recipe_over_max_minutes_is_rejected():
    with pytest.raises(llm_service.LLMResponseError):
        llm_service.check_options(_recipe(minutes=60), GenerateOptions(max_minutes=30))


def test_recipe_within_max_minutes_is_accepted():
    recipe = _recipe(minutes=20)
    assert llm_service.check_options(recipe, GenerateOptions(max_minutes=30)) is recipe


def test_generate_endpoint_passes_options_to_service(client, auth_headers, monkeypatch):
    client.post("/api/ingredients", json={"name": "arroz", "quantity": 500, "unit": "g"}, headers=auth_headers)
    received = {}

    async def fake_generate(items, options=None):
        received["options"] = options
        return _recipe()

    monkeypatch.setattr(llm_service, "generate_recipe", fake_generate)
    body = {"diet": "sin gluten", "max_minutes": 40, "servings": 2}
    res = client.post("/api/recipes/generate", json=body, headers=auth_headers)
    assert res.status_code == 201
    assert received["options"] == GenerateOptions(**body)


def test_generate_endpoint_rejects_invalid_options(client, auth_headers):
    client.post("/api/ingredients", json={"name": "arroz", "quantity": 500, "unit": "g"}, headers=auth_headers)
    res = client.post("/api/recipes/generate", json={"servings": 0}, headers=auth_headers)
    assert res.status_code == 422
