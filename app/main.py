from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import init_db
from app.routers import health, payload


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan managing database initialization and cleanup."""
    await init_db()
    yield


app = FastAPI(
    title="Caching Microservice",
    description=(
        "Microservice that transforms and interleaves string lists, "
        "minimizing external service calls by caching transformation outcomes "
        "and reusing generated payload identifiers."
    ),
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routers
app.include_router(payload.router)
app.include_router(health.router)


@app.get("/", tags=["Root"])
async def root():
    return {
        "service": "Caching Microservice",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health",
    }
