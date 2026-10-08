from fastapi.testclient import TestClient

from app.config import settings
from app.main import app


client = TestClient(app)


def test_home():
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {
        "message": "Task Manager API is running"
    }


def test_login():
    response = client.post(
        "/users/login",
        data={
            "username": settings.admin_username,
            "password": settings.admin_password
        }
    )

    assert response.status_code == 200

    data = response.json()

    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_get_current_user():
    login_response = client.post(
        "/users/login",
        data={
            "username": settings.admin_username,
            "password": settings.admin_password
        }
    )

    assert login_response.status_code == 200

    token = login_response.json()["access_token"]

    response = client.get(
        "/users/me",
        headers={
            "Authorization": f"Bearer {token}"
        }
    )

    assert response.status_code == 200

    data = response.json()

    assert data["username"] == settings.admin_username
    assert data["email"] == settings.admin_email

def test_get_current_user_without_token():
    response = client.get("/users/me")

    assert response.status_code == 401