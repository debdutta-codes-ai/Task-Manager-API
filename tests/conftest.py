import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app


# Provide a shared TestClient to tests that request it
@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


# Provide a valid admin access token for authenticated tests
@pytest.fixture
def admin_token(client):
    response = client.post(
        "/users/login",
        data={
            "username": settings.admin_username,
            "password": settings.admin_password
        }
    )

    assert response.status_code == 200

    return response.json()["access_token"]


# Provide authentication headers for admin requests
@pytest.fixture
def admin_headers(admin_token):
    return {
        "Authorization": f"Bearer {admin_token}"
    }