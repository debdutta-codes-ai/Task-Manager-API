from app.config import settings


# Test that the home endpoint returns the expected message
def test_home(client):
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {
        "message": "Task Manager API is running"
    }


# Test that login succeeds with valid admin credentials
def test_login(client):
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


# Test that a valid token allows access to the current user's information
def test_get_current_user(client, admin_headers):
    response = client.get(
        "/users/me",
        headers=admin_headers
    )

    assert response.status_code == 200

    data = response.json()

    assert data["username"] == settings.admin_username
    assert data["email"] == settings.admin_email


# Test that accessing the current user's information without a token is rejected
def test_get_current_user_without_token(client):
    response = client.get("/users/me")

    assert response.status_code == 401


# Test that login fails when the password is incorrect
def test_login_with_wrong_password(client):
    response = client.post(
        "/users/login",
        data={
            "username": settings.admin_username,
            "password": "DefinitelyWrongPassword123!"
        }
    )

    assert response.status_code == 401


# Test that an invalid JWT token is rejected
def test_get_current_user_with_invalid_token(client):
    response = client.get(
        "/users/me",
        headers={
            "Authorization": "Bearer invalid.fake.token"
        }
    )

    assert response.status_code == 401