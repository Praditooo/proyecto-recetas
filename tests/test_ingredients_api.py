def test_ingredients_require_authentication(client):
    assert client.get("/api/ingredients").status_code == 401


def test_ingredient_crud(client, auth_headers):
    created = client.post(
        "/api/ingredients", json={"name": "Arroz", "quantity": 500, "unit": "g"}, headers=auth_headers
    )
    assert created.status_code == 201
    ingredient_id = created.json()["id"]

    assert len(client.get("/api/ingredients", headers=auth_headers).json()) == 1

    updated = client.put(
        f"/api/ingredients/{ingredient_id}",
        json={"name": "Arroz", "quantity": 250, "unit": "g"},
        headers=auth_headers,
    )
    assert updated.json()["quantity"] == 250

    assert client.delete(f"/api/ingredients/{ingredient_id}", headers=auth_headers).status_code == 204
    assert client.get("/api/ingredients", headers=auth_headers).json() == []
