import logging
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import sessionmaker

from .config import DATABASE_URL, UPLOAD_DIRECTORY
from .database import Base, build_engine, create_schema, migrate_schema
from .admin_router import admin_router
from .routers import router
from .notifications import retry_pending_notifications
from .services import seed_database


def create_app(database_url: str | None = None, jwt_secret: str | None = None, upload_directory: str | Path | None = None) -> FastAPI:
    """Assemble infrastructure and domain routers; no endpoint logic lives here."""
    del jwt_secret  # Kept for existing test-call compatibility.
    url = database_url or DATABASE_URL
    upload_root = Path(upload_directory or UPLOAD_DIRECTORY)
    comment_directory = upload_root / "comments"; comment_directory.mkdir(parents=True, exist_ok=True)
    product_directory = upload_root / "products"; product_directory.mkdir(parents=True, exist_ok=True)
    engine = build_engine(url); sessions = sessionmaker(engine, expire_on_commit=False)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        create_schema(engine, url); Base.metadata.create_all(engine); migrate_schema(engine, url); seed_database(sessions)
        app.state.sessions = sessions; app.state.comment_upload_directory = comment_directory; app.state.product_upload_directory = product_directory; app.state.notifications_enabled = not url.startswith("sqlite")
        stop_retries = asyncio.Event()

        async def retry_loop() -> None:
            await asyncio.to_thread(retry_pending_notifications, sessions)
            while not stop_retries.is_set():
                try:
                    await asyncio.wait_for(stop_retries.wait(), timeout=300)
                except TimeoutError:
                    await asyncio.to_thread(retry_pending_notifications, sessions)

        retry_task = asyncio.create_task(retry_loop()) if app.state.notifications_enabled else None
        try:
            yield
        finally:
            stop_retries.set()
            if retry_task:
                await retry_task
            engine.dispose()

    app = FastAPI(title="Molecule Shop API", lifespan=lifespan)
    app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000", "http://localhost:3001", "http://localhost:5173"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
    app.mount("/uploads", StaticFiles(directory=str(upload_root)), name="uploads")

    @app.exception_handler(HTTPException)
    async def http_exception_handler(_: Request, error: HTTPException):
        return JSONResponse(status_code=error.status_code, content={"message": error.detail})

    @app.middleware("http")
    async def log_response(request: Request, call_next):
        response = await call_next(request)
        logging.getLogger("shop.api").info("%s %s %s", request.method, request.url.path, response.status_code)
        return response

    app.include_router(router)
    app.include_router(admin_router)
    return app
