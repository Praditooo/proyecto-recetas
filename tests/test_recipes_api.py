from app.schemas.recipe import RecipeContent, RecipeIngredient
from app.services import llm_service


def _fake_recipe() -> RecipeContent:
    return RecipeContent(
        name="Arroz con huevo",
        ingredients=[RecipeIngredient(name="arroz", quantity=200, unit="g")],
        steps=["Cocina el arroz", "Fríe el huevo"],
        estimated_minutes=25,
        difficulty="Fácil",
    )


def test_generate_requires_inventory(client, auth_headers):
    assert client.post("/api/recipes/generate", headers=auth_headers).status_code == 400


def test_generate_rate_and_delete_recipe(client, auth_headers, monkeypatch):
    client.post("/api/ingredients", json={"name": "arroz", "quantity": 500, "unit": "g"}, headers=auth_headers)

    async def fake_generate(items):
        return _fake_recipe()

    monkeypatch.setattr(llm_service, "generate_recipe", fake_generate)

    res = client.post("/api/recipes/generate", headers=auth_headers)
    assert res.status_code == 201
    recipe_id = res.json()["id"]

    assert client.get("/api/recipes", headers=auth_headers).json()[0]["id"] == recipe_id

    rated = client.post(f"/api/recipes/{recipe_id}/rating", json={"stars": 4}, headers=auth_headers)
    assert rated.json()["rating"] == 4
    assert client.post(f"/api/recipes/{recipe_id}/rating", json={"stars": 6}, headers=auth_headers).status_code == 422

    assert client.delete(f"/api/recipes/{recipe_id}", headers=auth_headers).status_code == 204
    assert client.get("/api/recipes", headers=auth_headers).json() == []
