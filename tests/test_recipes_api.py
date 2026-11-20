from sqlalchemy import event

from app.database import get_db
from app.main import app
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

    async def fake_generate(items, options=None):
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


def _seed(client, auth_headers, monkeypatch, variants):
    """Crea una receta por cada diccionario de cambios sobre la receta falsa y devuelve sus ids."""
    client.post("/api/ingredients", json={"name": "arroz", "quantity": 500, "unit": "g"}, headers=auth_headers)
    pending = iter(variants)

    async def fake_generate(items, options=None):
        return _fake_recipe().model_copy(update=next(pending))

    monkeypatch.setattr(llm_service, "generate_recipe", fake_generate)
    return [client.post("/api/recipes/generate", headers=auth_headers).json()["id"] for _ in variants]


def _count_queries(client, path, headers):
    """Cuenta las sentencias SQL que ejecuta una peticion."""
    engine = next(app.dependency_overrides[get_db]()).get_bind()
    statements = []

    def on_execute(*_):
        statements.append(1)

    event.listen(engine, "before_cursor_execute", on_execute)
    try:
        assert client.get(path, headers=headers).status_code == 200
    finally:
        event.remove(engine, "before_cursor_execute", on_execute)
    return len(statements)


def test_history_loads_ratings_without_n_plus_one_queries(client, auth_headers, monkeypatch):
    for recipe_id in _seed(client, auth_headers, monkeypatch, [{}, {}]):
        client.post(f"/api/recipes/{recipe_id}/rating", json={"stars": 3}, headers=auth_headers)
    with_two = _count_queries(client, "/api/recipes", auth_headers)

    for recipe_id in _seed(client, auth_headers, monkeypatch, [{}, {}, {}]):
        client.post(f"/api/recipes/{recipe_id}/rating", json={"stars": 4}, headers=auth_headers)
    with_five = _count_queries(client, "/api/recipes", auth_headers)

    assert with_five == with_two
    ratings = [r["rating"] for r in client.get("/api/recipes", headers=auth_headers).json()]
    assert ratings == [4, 4, 4, 3, 3]


def test_history_sorts_oldest_first(client, auth_headers, monkeypatch):
    first, second, third = _seed(client, auth_headers, monkeypatch, [{}, {}, {}])

    newest = client.get("/api/recipes", headers=auth_headers).json()
    oldest = client.get("/api/recipes", params={"sort": "oldest"}, headers=auth_headers).json()

    assert [r["id"] for r in newest] == [third, second, first]
    assert [r["id"] for r in oldest] == [first, second, third]


def test_remove_rating(client, auth_headers, monkeypatch):
    (recipe_id,) = _seed(client, auth_headers, monkeypatch, [{}])
    client.post(f"/api/recipes/{recipe_id}/rating", json={"stars": 5}, headers=auth_headers)

    removed = client.delete(f"/api/recipes/{recipe_id}/rating", headers=auth_headers)
    assert removed.status_code == 200
    assert removed.json()["rating"] is None
    assert client.get(f"/api/recipes/{recipe_id}", headers=auth_headers).json()["rating"] is None

    # Quitarla otra vez no falla, y una receta inexistente responde 404.
    assert client.delete(f"/api/recipes/{recipe_id}/rating", headers=auth_headers).status_code == 200
    assert client.delete("/api/recipes/9999/rating", headers=auth_headers).status_code == 404
