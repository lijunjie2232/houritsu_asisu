from fastapi import FastAPI

from app.api.v1.api import api_router
from app.core.config.settings import settings
from app.core.db.base import engine
from app.models.conversation import Base  # Import all models to create tables

# Create database tables
Base.metadata.create_all(bind=engine)

# Create FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME, openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Include API routes
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/")
def read_root():
    return {
        "message": "Welcome to the Japanese Law AI Agent API",
        "project": settings.PROJECT_NAME,
        "version": "1.0.0",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
