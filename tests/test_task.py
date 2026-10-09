from app.config import settings


# Test that creating a task without assigned_to_email is rejected
def test_create_task_requires_assigned_to_email(client, admin_headers):
    # Attempt to create a task without the required assigned_to_email field
    response = client.post(
        "/tasks/",
        headers=admin_headers,
        json={
            "title": "Test task",
            "description": "Test task description",
            "status": "pending",
            "team_id": None
        }
    )

    # Verify that validation rejects the request
    assert response.status_code == 422


# Test that creating a task without an authentication token is rejected
def test_create_task_without_token(client):
    # Send a task creation request without an Authorization header
    response = client.post(
        "/tasks/",
        json={
            "title": "Unauthorized task",
            "description": "This task should not be created",
            "status": "pending",
            "assigned_to_email": "admin@example.com",
            "team_id": None
        }
    )

    # Verify that the API rejects the unauthenticated request
    assert response.status_code == 401


# Test that creating a task with an invalid authentication token is rejected
def test_create_task_with_invalid_token(client):
    # Send a task creation request with a fake bearer token
    response = client.post(
        "/tasks/",
        headers={
            "Authorization": "Bearer invalid.fake.token"
        },
        json={
            "title": "Invalid token task",
            "description": "This task should not be created",
            "status": "pending",
            "assigned_to_email": "admin@example.com",
            "team_id": None
        }
    )

    # Verify that the API rejects the invalid token
    assert response.status_code == 401


# Test that retrieving a task without an authentication token is rejected
def test_get_task_without_token(client):
    # Request task ID 1 without providing an Authorization header
    response = client.get("/tasks/1")

    # Verify that the API rejects the unauthenticated request
    assert response.status_code == 401


# Test that retrieving a task with an invalid token is rejected
def test_get_task_with_invalid_token(client):
    # Request task ID 1 using a deliberately fake authentication token
    response = client.get(
        "/tasks/1",
        headers={
            "Authorization": "Bearer invalid.fake.token"
        }
    )

    # Verify that the API rejects the invalid token
    assert response.status_code == 401

# Test that an admin can create a task and retrieve it afterward
def test_create_task_success(client, admin_headers):
    # Create a new task with valid data
    create_response = client.post(
        "/tasks/",
        headers=admin_headers,
        json={
            "title": "Pytest task",
            "description": "Task created during automated testing",
            "status": "pending",
            "assigned_to_email": settings.admin_email,
            "team_id": None
        }
    )

    # Verify that task creation succeeds
    assert create_response.status_code == 201

    # Extract the new task's ID from the response
    created_task = create_response.json()
    task_id = created_task["id"]

    # Verify that the returned task has the expected details
    assert created_task["title"] == "Pytest task"
    assert created_task["description"] == "Task created during automated testing"
    assert created_task["status"] == "pending"
    assert created_task["assigned_to_email"] == settings.admin_email

    # Retrieve the task using its actual ID and the admin's token
    get_response = client.get(
        f"/tasks/{task_id}",
        headers=admin_headers
    )

    # Verify that the task can be retrieved successfully
    assert get_response.status_code == 200

    # Verify that the retrieved task matches the task we created
    retrieved_task = get_response.json()
    assert retrieved_task["id"] == task_id
    assert retrieved_task["title"] == "Pytest task"
    assert retrieved_task["assigned_to_email"] == settings.admin_email