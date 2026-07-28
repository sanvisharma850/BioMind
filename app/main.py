from fastapi import FastAPI

from app.config import PROJECT_NAME
from app.config import VERSION

from app.database.database import Base
from app.database.database import engine

from app.api.routes import router

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=PROJECT_NAME,
    version=VERSION,
)

app.include_router(router)