from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import exports, generation, projects, uploads, validation, workspace
from app.core.config import get_settings
from app.db.base import Base
from app.db.session import engine


settings = get_settings()


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(projects.router)
    app.include_router(uploads.router)
    app.include_router(generation.router)
    app.include_router(validation.router)
    app.include_router(workspace.router)
    app.include_router(exports.router)

    @app.on_event("startup")
    def create_local_schema() -> None:
        Base.metadata.create_all(bind=engine)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "service": settings.app_name}

    return app


app = create_app()

