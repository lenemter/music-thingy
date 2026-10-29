from fastapi.testclient import TestClient


def test_health_check(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


def test_register_success(client: TestClient):
    payload = {
        "email": "testuser@example.com",
        "password": "strongpassword123",
        "display_name": "Test User",
    }
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "testuser@example.com"
    assert data["display_name"] == "Test User"
    assert "id" in data
    assert "password" not in data


def test_register_duplicate_email(client: TestClient):
    payload = {
        "email": "duplicate@example.com",
        "password": "password12345",
        "display_name": "First User",
    }
    res1 = client.post("/api/auth/register", json=payload)
    assert res1.status_code == 201

    res2 = client.post("/api/auth/register", json=payload)
    assert res2.status_code == 400
    assert "already exists" in res2.json()["detail"]


def test_register_short_password(client: TestClient):
    payload = {
        "email": "shortpw@example.com",
        "password": "short",
        "display_name": "Short PW",
    }
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 422


def test_login_json_success(client: TestClient):
    # 1. Register
    reg_payload = {
        "email": "loginuser@example.com",
        "password": "validpassword123",
        "display_name": "Login User",
    }
    client.post("/api/auth/register", json=reg_payload)

    # 2. Login via JSON
    login_payload = {
        "email": "loginuser@example.com",
        "password": "validpassword123",
    }
    response = client.post("/api/auth/token", json=login_payload)
    assert response.status_code == 200
    data = response.json()
    assert "access" in data
    assert "refresh" in data
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


def test_login_form_success(client: TestClient):
    # 1. Register
    reg_payload = {
        "email": "formuser@example.com",
        "password": "validpassword123",
    }
    client.post("/api/auth/register", json=reg_payload)

    # 2. Login via Form Data (Swagger UI style)
    response = client.post(
        "/api/auth/token",
        data={"username": "formuser@example.com", "password": "validpassword123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data


def test_login_invalid_password(client: TestClient):
    reg_payload = {
        "email": "wrongpw@example.com",
        "password": "correctpassword123",
    }
    client.post("/api/auth/register", json=reg_payload)

    response = client.post(
        "/api/auth/token",
        json={"email": "wrongpw@example.com", "password": "wrongpassword123"},
    )
    assert response.status_code == 401


def test_login_nonexistent_user(client: TestClient):
    response = client.post(
        "/api/auth/token",
        json={"email": "nonexistent@example.com", "password": "password123"},
    )
    assert response.status_code == 401


def test_get_current_user_me(client: TestClient):
    # Register & Login
    client.post(
        "/api/auth/register",
        json={
            "email": "me@example.com",
            "password": "password12345",
            "display_name": "Me User",
        },
    )
    login_res = client.post(
        "/api/auth/token",
        json={"email": "me@example.com", "password": "password12345"},
    )
    token = login_res.json()["access_token"]

    # Call /api/auth/me
    headers = {"Authorization": f"Bearer {token}"}
    me_res = client.get("/api/auth/me", headers=headers)
    assert me_res.status_code == 200
    data = me_res.json()
    assert data["email"] == "me@example.com"
    assert data["display_name"] == "Me User"
    assert data["is_active"] is True


def test_get_me_unauthorized(client: TestClient):
    response = client.get("/api/auth/me")
    assert response.status_code == 401

    response = client.get("/api/auth/me", headers={"Authorization": "Bearer invalidtoken"})
    assert response.status_code == 401


def test_token_refresh(client: TestClient):
    # Register & Login
    client.post(
        "/api/auth/register",
        json={
            "email": "refresh@example.com",
            "password": "password12345",
        },
    )
    login_res = client.post(
        "/api/auth/token",
        json={"email": "refresh@example.com", "password": "password12345"},
    )
    refresh_token = login_res.json()["refresh"]

    # Refresh token
    refresh_res = client.post(
        "/api/auth/token/refresh",
        json={"refresh": refresh_token},
    )
    assert refresh_res.status_code == 200
    data = refresh_res.json()
    new_access_token = data["access"]
    assert new_access_token

    # Verify new token works on /api/auth/me
    headers = {"Authorization": f"Bearer {new_access_token}"}
    me_res = client.get("/api/auth/me", headers=headers)
    assert me_res.status_code == 200
    assert me_res.json()["email"] == "refresh@example.com"


def test_token_refresh_with_access_token_fails(client: TestClient):
    # Attempting to use access token at refresh endpoint should fail
    client.post(
        "/api/auth/register",
        json={
            "email": "failrefresh@example.com",
            "password": "password12345",
        },
    )
    login_res = client.post(
        "/api/auth/token",
        json={"email": "failrefresh@example.com", "password": "password12345"},
    )
    access_token = login_res.json()["access"]

    refresh_res = client.post(
        "/api/auth/token/refresh",
        json={"refresh": access_token},
    )
    assert refresh_res.status_code == 401
