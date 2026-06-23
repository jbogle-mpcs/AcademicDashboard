from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.database import Base, engine

# Must be imported before create_all so SQLAlchemy's mapper registry
# is fully populated when we call Base.metadata.create_all().
import app.models  # noqa: F401

from app.api import (
    health,
    students,
    assessments,
    canvas,
    auth,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api/health", tags=["Health"])
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(students.router, prefix="/api/students", tags=["Students"])
app.include_router(assessments.router, prefix="/api/assessments", tags=["Assessments"])
app.include_router(canvas.router, prefix="/api/canvas", tags=["Canvas"])


@app.get("/")
async def root():
    return {
        "application": settings.APP_NAME,
        "version": "1.0.0",
        "status": "online",
    }