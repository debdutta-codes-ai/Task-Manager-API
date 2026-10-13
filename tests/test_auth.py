from app.config import settings
from datetime import timedelta
from app import auth

# Test that the home endpoint responds successfully.
def test_home(client):
    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["message"] == "Task Manager API is running"


# Test that the isolated test admin can log in.
def test_login(client):
    response = client.post(
        "/users/login",
        data={
            "username": "testadmin",
            "password": "TestAdmin123!",
        },
    )

    assert response.status_code == 200
    assert "access_token" in response.json()


# Test that the authenticated user endpoint returns the test admin.
def test_get_current_user(client, admin_headers):
    response = client.get(
        "/users/me",
        headers=admin_headers,
    )

    assert response.status_code == 200

    data = response.json()
    assert data["username"] == "testadmin"
    assert data["email"] == "testadmin@example.com"


# Test that requesting the current user without a token is rejected.
def test_get_current_user_without_token(client):
    response = client.get("/users/me")

    assert response.status_code == 401


# Test that an incorrect password is rejected.
def test_login_with_wrong_password(client):
    response = client.post(
        "/users/login",
        data={
            "username": "testadmin",
            "password": "WrongPassword123!",
        },
    )

    assert response.status_code == 401


# Test that an invalid JWT is rejected.
def test_get_current_user_with_invalid_token(client):
    response = client.get(
        "/users/me",
        headers={"Authorization": "Bearer invalid.fake.token"},
    )

    assert response.status_code == 401

def test_inactive_user_cannot_access_protected_endpoint(
    client, test_db
):
    from app import models

    user = (
        test_db.query(models.User)
        .filter(models.User.username == "testuser")
        .first()
    )

    # Make the account inactive.
    user.status = "inactive"
    test_db.commit()

    # Log in and obtain a token.
    login_response = client.post(
        "/users/login",
        data={
            "username": "testuser",
            "password": "TestUser123!",
        },
    )

    # The login endpoint may itself reject inactive users.
    if login_response.status_code != 200:
        assert login_response.status_code == 401
        return

    headers = {
        "Authorization": (
            f"Bearer {login_response.json()['access_token']}"
        )
    }

    # Try to access a protected endpoint.
    response = client.get(
        "/users/me",
        headers=headers,
    )

    assert response.status_code == 401

def test_get_current_user_with_expired_token(client):
    expired_token = auth.create_access_token(
        data={"sub": "1"},
        expires_delta=timedelta(seconds=-1),
    )

    response = client.get(
        "/users/me",
        headers={
            "Authorization": f"Bearer {expired_token}"
        },
    )

    assert response.status_code == 401