from tests.conftest import USER


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
