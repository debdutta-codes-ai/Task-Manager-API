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


# # Test that a user without manage_users permission
# # cannot access the user-management endpoint
# def test_get_users_without_manage_users_permission(
#     client,
#     admin_headers
# ):
#     # Fetch the admin user from the database
#     from app.database import SessionLocal
#     from app import models

#     db = SessionLocal()

#     try:
#         admin = (
#             db.query(models.User)
#             .filter(
#                 models.User.username == settings.admin_username
#             )
#             .first()
#         )

#         assert admin is not None
#         assert admin.role is not None

#         # Save the original permissions so we can restore them
#         original_permissions = list(admin.role.permissions)

#         # Remove manage_users temporarily
#         admin.role.permissions = [
#             permission
#             for permission in admin.role.permissions
#             if permission.name != "manage_users"
#         ]

#         db.commit()

#         # Try to access the protected endpoint
#         response = client.get(
#             "/users/",
#             headers=admin_headers
#         )

#         # Access should be forbidden without manage_users
#         assert response.status_code == 403

#         # Restore the original permissions
#         admin.role.permissions = original_permissions
#         db.commit()

#     finally:
#         db.close()