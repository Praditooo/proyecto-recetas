"""Pruebas del historial: búsqueda, filtros, orden y paginación de GET /api/recipes."""
import pytest

from app.schemas.recipe import RecipeContent, RecipeIngredient
from app.services import llm_service

RECIPES = [
    ("Arroz con huevo", "Fácil"),
    ("Arroz con pollo", "Media"),
    ("Lasaña de verduras", "Difícil"),
    ("Tortilla 100% papa", "Fácil"),
]


@pytest.fixture
def history(client, auth_headers, monkeypatch):
    """Crea las recetas de RECIPES (en ese orden) y devuelve sus ids por nombre."""
    client.post("/api/ingredients", json={"name": "arroz", "quantity": 500, "unit": "g"}, headers=auth_headers)
    queue = list(RECIPES)

    async def fake_generate(items, options=None):
        name, difficulty = queue.pop(0)
        return RecipeContent(
            name=name,
            ingredients=[RecipeIngredient(name="arroz", quantity=100, unit="g")],
            steps=["Cocinar"],
            estimated_minutes=20,
            difficulty=difficulty,
        )

    monkeypatch.setattr(llm_service, "generate_recipe", fake_generate)
    ids = {}
    for name, _ in RECIPES:
        ids[name] = client.post("/api/recipes/generate", headers=auth_headers).json()["id"]
    return ids


def _names(client, auth_headers, **params):
    res = client.get("/api/recipes", params=params, headers=auth_headers)
    assert res.status_code == 200
    return [r["name"] for r in res.json()], res


def test_default_order_is_newest_first_with_total_header(client, auth_headers, history):
    names, res = _names(client, auth_headers)
    assert names == [name for name, _ in reversed(RECIPES)]
    assert res.headers["X-Total-Count"] == "4"


def test_search_by_name_is_case_insensitive(client, auth_headers, history):
    names, res = _names(client, auth_headers, q="ARROZ")
    assert sorted(names) == ["Arroz con huevo", "Arroz con pollo"]
    assert res.headers["X-Total-Count"] == "2"


def test_search_treats_percent_as_plain_text(client, auth_headers, history):
    names, _ = _names(client, auth_headers, q="%")
    assert names == ["Tortilla 100% papa"]


def test_filter_by_difficulty(client, auth_headers, history):
    names, _ = _names(client, auth_headers, difficulty="Fácil")
    assert sorted(names) == ["Arroz con huevo", "Tortilla 100% papa"]


def test_filter_by_min_rating_and_sort_by_rating(client, auth_headers, history):
    client.post(f"/api/recipes/{history['Arroz con pollo']}/rating", json={"stars": 3}, headers=auth_headers)
    client.post(f"/api/recipes/{history['Lasaña de verduras']}/rating", json={"stars": 5}, headers=auth_headers)

    names, _ = _names(client, auth_headers, min_rating=4)
    assert names == ["Lasaña de verduras"]

    names, _ = _names(client, auth_headers, sort="rating")
    assert names[:2] == ["Lasaña de verduras", "Arroz con pollo"]
    assert len(names) == 4  # las no calificadas también aparecen, al final


def test_pagination_with_limit_and_offset(client, auth_headers, history):
    first, res = _names(client, auth_headers, limit=3, offset=0)
    second, _ = _names(client, auth_headers, limit=3, offset=3)
    assert len(first) == 3 and len(second) == 1
    assert set(first).isdisjoint(second)
    assert res.headers["X-Total-Count"] == "4"


@pytest.mark.parametrize(
    "params",
    [{"difficulty": "Imposible"}, {"min_rating": 6}, {"sort": "nombre"}, {"limit": 0}, {"limit": 101}, {"offset": -1}],
)
def test_invalid_filters_return_422(client, auth_headers, params):
    assert client.get("/api/recipes", params=params, headers=auth_headers).status_code == 422


def test_history_does_not_show_other_users_recipes(client, auth_headers, history):
    other = {"email": "beto@example.com", "full_name": "Beto", "password": "secreto456"}
    client.post("/api/auth/register", json=other)
    token = client.post(
        "/api/auth/login", data={"username": other["email"], "password": other["password"]}
    ).json()["access_token"]
    res = client.get("/api/recipes", headers={"Authorization": f"Bearer {token}"})
    assert res.json() == []
    assert res.headers["X-Total-Count"] == "0"
