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


def test_search_ingredients(client, auth_headers):
    """Buscar ingredientes por nombre con el parámetro ?q=."""
    client.post("/api/ingredients", json={"name": "Tomate", "quantity": 3, "unit": "unidad"}, headers=auth_headers)
    client.post("/api/ingredients", json={"name": "Cebolla", "quantity": 2, "unit": "unidad"}, headers=auth_headers)
    client.post("/api/ingredients", json={"name": "Tomate cherry", "quantity": 10, "unit": "unidad"}, headers=auth_headers)

    # Buscar "tomate" debe devolver 2 resultados
    results = client.get("/api/ingredients?q=tomate", headers=auth_headers).json()
    assert len(results) == 2
    names = [r["name"] for r in results]
    assert "Tomate" in names
    assert "Tomate cherry" in names

    # Buscar "cebolla" debe devolver 1 resultado
    results = client.get("/api/ingredients?q=cebolla", headers=auth_headers).json()
    assert len(results) == 1
    assert results[0]["name"] == "Cebolla"

    # Buscar algo que no existe devuelve lista vacía
    results = client.get("/api/ingredients?q=pepino", headers=auth_headers).json()
    assert len(results) == 0

    # Sin parámetro q devuelve todos
    results = client.get("/api/ingredients", headers=auth_headers).json()
    assert len(results) == 3


def test_merge_duplicate_ingredient(client, auth_headers):
    """Al crear un ingrediente duplicado (mismo nombre y unidad), se fusionan sumando cantidades."""
    res1 = client.post(
        "/api/ingredients", json={"name": "Arroz", "quantity": 500, "unit": "g"}, headers=auth_headers
    )
    assert res1.status_code == 201
    first_id = res1.json()["id"]

    # Crear el mismo ingrediente de nuevo: debe fusionarse
    res2 = client.post(
        "/api/ingredients", json={"name": "Arroz", "quantity": 300, "unit": "g"}, headers=auth_headers
    )
    assert res2.status_code == 201
    assert res2.json()["id"] == first_id
    assert res2.json()["quantity"] == 800  # 500 + 300

    # Solo hay 1 ingrediente en el inventario
    items = client.get("/api/ingredients", headers=auth_headers).json()
    assert len(items) == 1


def test_no_merge_different_unit(client, auth_headers):
    """Ingredientes con mismo nombre pero distinta unidad NO se fusionan."""
    client.post("/api/ingredients", json={"name": "Leche", "quantity": 1, "unit": "l"}, headers=auth_headers)
    client.post("/api/ingredients", json={"name": "Leche", "quantity": 500, "unit": "ml"}, headers=auth_headers)

    items = client.get("/api/ingredients", headers=auth_headers).json()
    assert len(items) == 2


def test_edit_all_fields(client, auth_headers):
    """La edición en línea permite cambiar nombre, cantidad y unidad."""
    res = client.post(
        "/api/ingredients", json={"name": "Azucar", "quantity": 1, "unit": "kg"}, headers=auth_headers
    )
    ingredient_id = res.json()["id"]

    updated = client.put(
        f"/api/ingredients/{ingredient_id}",
        json={"name": "Azúcar morena", "quantity": 500, "unit": "g"},
        headers=auth_headers,
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Azúcar morena"
    assert updated.json()["quantity"] == 500
    assert updated.json()["unit"] == "g"


def test_rejects_invalid_unit_via_api(client, auth_headers):
    """El API rechaza unidades que no están en la lista predefinida."""
    res = client.post(
        "/api/ingredients", json={"name": "Agua", "quantity": 1, "unit": "barril"}, headers=auth_headers
    )
    assert res.status_code == 422


def test_ingredient_not_accessible_by_other_user(client, auth_headers):
    """Un ingrediente de un usuario no puede ser visto ni editado por otro usuario."""
    # Usuario A crea un ingrediente
    res = client.post(
        "/api/ingredients", json={"name": "Mantequilla", "quantity": 200, "unit": "g"}, headers=auth_headers
    )
    ingredient_id = res.json()["id"]

    # Usuario B se registra y obtiene su token
    client.post("/api/auth/register", json={"email": "otro@example.com", "full_name": "Otro", "password": "clave1234"})
    login = client.post("/api/auth/login", data={"username": "otro@example.com", "password": "clave1234"})
    other_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    # Usuario B intenta acceder al ingrediente de A: debe recibir 404
    assert client.get(f"/api/ingredients/{ingredient_id}", headers=other_headers).status_code == 404
    assert client.put(
        f"/api/ingredients/{ingredient_id}",
        json={"name": "Mantequilla", "quantity": 50, "unit": "g"},
        headers=other_headers,
    ).status_code == 404
    assert client.delete(f"/api/ingredients/{ingredient_id}", headers=other_headers).status_code == 404


def test_max_ingredients_limit(client, auth_headers):
    """No se pueden agregar más de MAX_INGREDIENTS_PER_USER ingredientes distintos."""
    from app.schemas.ingredient import MAX_INGREDIENTS_PER_USER

    # Crear ingredientes hasta el límite
    for i in range(MAX_INGREDIENTS_PER_USER):
        res = client.post(
            "/api/ingredients",
            json={"name": f"ingrediente_{i}", "quantity": 1, "unit": "unidad"},
            headers=auth_headers,
        )
        assert res.status_code == 201

    # El siguiente debe ser rechazado
    over_limit = client.post(
        "/api/ingredients",
        json={"name": "ingrediente_extra", "quantity": 1, "unit": "unidad"},
        headers=auth_headers,
    )
    assert over_limit.status_code == 400
    assert "100" in over_limit.json()["detail"]
