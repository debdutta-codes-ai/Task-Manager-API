from fastapi import FastAPI

from app.database import Base, engine
from app import models
from app.routes.teams import router as teams_router
from app.routes.task import router as task_router
from app.routes.users import router as user_router
from app.routes.roles import router as roles_router

Base.metadata.create_all(bind=engine)

app = FastAPI()

@app.get("/")
def home():
    return {"message": "Task Manager API is running"}


app.include_router(task_router)
app.include_router(user_router)
app.include_router(teams_router)
app.include_router(roles_router)