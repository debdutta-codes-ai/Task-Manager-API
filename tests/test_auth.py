from app.config import settings


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


