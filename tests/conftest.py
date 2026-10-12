# import pytest
# from fastapi.testclient import TestClient

# from app.config import settings
# from app.main import app


# # Provide a shared TestClient to tests that request it
# @pytest.fixture
# def client():
#     with TestClient(app) as test_client:
#         yield test_client


# # Provide a valid admin access token for authenticated tests
# @pytest.fixture
# def admin_token(client):
#     response = client.post(
#         "/users/login",
#         data={
#             "username": settings.admin_username,
#             "password": settings.admin_password
#         }
#     )

#     assert response.status_code == 200

#     return response.json()["access_token"]


# # Provide authentication headers for admin requests
# @pytest.fixture
# def admin_headers(admin_token):
#     return {
#         "Authorization": f"Bearer {admin_token}"
#     }

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app import models
from app.auth import password_hash
from app import crud


# Use an isolated in-memory SQLite database for each test.
@pytest.fixture
def test_db():
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=test_engine,
    )

    Base.metadata.create_all(bind=test_engine)

    db = TestingSessionLocal()

    # Create the roles required by the tests.
    admin_role = models.Role(name="admin", description="Test admin")
    manager_role = models.Role(name="manager", description="Test manager")
    user_role = models.Role(name="user", description="Test user")

    # Create the permissions used by the task routes.
    permission_names = [
        "read_all_tasks",
        "read_own_task",
        "read_team_tasks",
        "create_task",
        "update_any_task",
        "update_own_task",
        "update_team_task",
        "delete_any_task",
        "delete_own_task",
        "delete_team_task",
        "manage_users",
        "change_roles",
    ]

    permissions = {
        name: models.Permission(name=name, description=f"Test {name}")
        for name in permission_names
    }

    db.add_all([admin_role, manager_role, user_role])
    db.add_all(permissions.values())
    db.flush()

    # Give the admin all permissions.
    admin_role.permissions = list(permissions.values())

    # Give the manager only the permissions needed for team tasks.
    manager_role.permissions = [
        permissions[name]
        for name in [
            "read_own_task",
            "read_team_tasks",
            "create_task",
            "update_own_task",
            "update_team_task",
            "delete_own_task",
            "delete_team_task",
        ]
    ]

    # Give a regular user only their own-task permissions.
    user_role.permissions = [
        permissions[name]
        for name in [
            "read_own_task",
            "create_task",
            "update_own_task",
            "delete_own_task",
        ]
    ]

    # Create test users with valid password hashes.
    admin = models.User(
        username="testadmin",
        email="testadmin@example.com",
        password_hash=password_hash.hash("TestAdmin123!"),
        role=admin_role,
        status="active",
    )

    manager = models.User(
        username="testmanager",
        email="testmanager@example.com",
        password_hash=password_hash.hash("TestManager123!"),
        role=manager_role,
        status="active",
    )

    user = models.User(
        username="testuser",
        email="testuser@example.com",
        password_hash=password_hash.hash("TestUser123!"),
        role=user_role,
        status="active",
    )

    db.add_all([admin, manager, user])
    db.commit()

    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=test_engine)
        test_engine.dispose()


# Override the application's database dependency for each test.
@pytest.fixture
def client(test_db):
    def override_get_db():
        try:
            yield test_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


# Provide authentication headers for the isolated test admin.
@pytest.fixture
def admin_headers(client):
    response = client.post(
        "/users/login",
        data={
            "username": "testadmin",
            "password": "TestAdmin123!",
        },
    )

    assert response.status_code == 200

    return {
        "Authorization": f"Bearer {response.json()['access_token']}"
    }