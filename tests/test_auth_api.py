from tests.conftest import USER
from app.security import create_access_token


def test_register_and_login(client):
    res = client.post("/api/auth/register", json=USER)
    assert res.status_code == 201
    assert "password" not in res.text

    res = client.post("/api/auth/login", data={"username": USER["email"], "password": USER["password"]})
    assert res.status_code == 200
    assert res.json()["token_type"] == "bearer"


def test_duplicate_email_is_rejected(client):
    client.post("/api/auth/register", json=USER)
    assert client.post("/api/auth/register", json=USER).status_code == 409


def test_wrong_password_returns_401(client):
    client.post("/api/auth/register", json=USER)
    res = client.post("/api/auth/login", data={"username": USER["email"], "password": "incorrecta1"})
    assert res.status_code == 401

def test_me_requires_token(client):
    assert client.get("/api/auth/me").status_code == 401


def test_me_rejects_invalid_token(client):
    res = client.get("/api/auth/me", headers={"Authorization": "Bearer token-falso"})
    assert res.status_code == 401
    assert res.headers["www-authenticate"] == "Bearer"


def test_me_rejects_token_of_nonexistent_user(client):
    token = create_access_token(9999)
    res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 401


def test_me_returns_current_user(client, auth_headers):
    res = client.get("/api/auth/me", headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["email"] == USER["email"]

def test_update_name(client, auth_headers):
    res = client.patch("/api/auth/me", json={"full_name": "  Ana   Lucía "}, headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["full_name"] == "Ana Lucía"
    assert client.get("/api/auth/me", headers=auth_headers).json()["full_name"] == "Ana Lucía"


def test_update_name_requires_auth(client):
    assert client.patch("/api/auth/me", json={"full_name": "Ana"}).status_code == 401


def test_update_name_rejects_blank(client, auth_headers):
    res = client.patch("/api/auth/me", json={"full_name": "   "}, headers=auth_headers)
    assert res.status_code == 422

def test_change_password(client, auth_headers):
    res = client.post(
        "/api/auth/change-password",
        json={"current_password": USER["password"], "new_password": "nueva-clave1"},
        headers=auth_headers,
    )
    assert res.status_code == 204

    old = client.post("/api/auth/login", data={"username": USER["email"], "password": USER["password"]})
    assert old.status_code == 401
    new = client.post("/api/auth/login", data={"username": USER["email"], "password": "nueva-clave1"})
    assert new.status_code == 200


def test_change_password_wrong_current(client, auth_headers):
    res = client.post(
        "/api/auth/change-password",
        json={"current_password": "incorrecta1", "new_password": "nueva-clave1"},
        headers=auth_headers,
    )
    assert res.status_code == 400


def test_change_password_must_differ(client, auth_headers):
    res = client.post(
        "/api/auth/change-password",
        json={"current_password": USER["password"], "new_password": USER["password"]},
        headers=auth_headers,
    )
    assert res.status_code == 400


def test_change_password_rejects_weak_new(client, auth_headers):
    res = client.post(
        "/api/auth/change-password",
        json={"current_password": USER["password"], "new_password": "sololetras"},
        headers=auth_headers,
    )
    assert res.status_code == 422

def test_delete_account(client, auth_headers):
    client.post(
        "/api/ingredients", json={"name": "arroz", "quantity": 1, "unit": "kg"}, headers=auth_headers
    )
    res = client.request("DELETE", "/api/auth/me", json={"password": USER["password"]}, headers=auth_headers)
    assert res.status_code == 204

    # El token viejo ya no sirve y el usuario no puede iniciar sesión
    assert client.get("/api/auth/me", headers=auth_headers).status_code == 401
    login = client.post("/api/auth/login", data={"username": USER["email"], "password": USER["password"]})
    assert login.status_code == 401

    # Si se registra de nuevo, su inventario empieza vacío (se borró en cascada)
    new_headers = _register_again(client)
    assert client.get("/api/ingredients", headers=new_headers).json() == []


def test_delete_account_wrong_password(client, auth_headers):
    res = client.request("DELETE", "/api/auth/me", json={"password": "incorrecta1"}, headers=auth_headers)
    assert res.status_code == 400
    assert client.get("/api/auth/me", headers=auth_headers).status_code == 200


def _register_again(client):
    client.post("/api/auth/register", json=USER)
    res = client.post("/api/auth/login", data={"username": USER["email"], "password": USER["password"]})
    return {"Authorization": f"Bearer {res.json()['access_token']}"}

def test_login_page_has_password_toggle(client):
    res = client.get("/")
    assert res.status_code == 200
    assert "Mostrar contraseña" in res.text