import json

import pytest

from app.services.llm_service import LLMResponseError, parse_recipe_response

VALID = {
    "name": "Arroz con huevo",
    "ingredients": [{"name": "arroz", "quantity": 200, "unit": "g"}],
    "steps": ["Cocina el arroz", "Fríe el huevo"],
    "estimated_minutes": 25,
    "difficulty": "Fácil",
}


def test_parses_valid_json():
    recipe = parse_recipe_response(json.dumps(VALID))
    assert recipe.name == "Arroz con huevo"
    assert recipe.estimated_minutes == 25
    assert recipe.ingredients[0].unit == "g"


def test_parses_json_wrapped_in_markdown_fence():
    raw = "```json\n" + json.dumps(VALID) + "\n```"
    assert parse_recipe_response(raw).difficulty == "Fácil"


def test_rejects_text_without_json():
    with pytest.raises(LLMResponseError):
        parse_recipe_response("Claro, aquí tienes una receta deliciosa")


def test_rejects_invalid_difficulty():
    bad = {**VALID, "difficulty": "Imposible"}
    with pytest.raises(LLMResponseError):
        parse_recipe_response(json.dumps(bad))
