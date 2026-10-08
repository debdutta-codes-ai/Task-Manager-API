from fastapi import FastAPI

from app.routes import (
    task,
    users,
    teams,
    roles,
    permission
)

app = FastAPI()

@app.get("/")
def home():
    return {"message": "Task Manager API is running"}

app.include_router(task.router)
app.include_router(users.router)
app.include_router(teams.router)
app.include_router(roles.router)
app.include_router(permission.router)