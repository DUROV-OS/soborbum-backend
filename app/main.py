from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect

from app.ai.router import app as ai_app
from app.clients.router import app as clients_app
from app.common.files import router as files_router
from app.core.config import settings
from app.cycle.router import app as cycle_app
from app.db import import_all_models  # noqa: F401  (registers all models with Base.metadata)
from app.db.base import Base
from app.db.session import engine, SessionLocal
from app.installation.router import app as installation_app
from app.marketing.router import app as marketing_app
from app.production.router import app as production_app
from app.tasks.router import app as tasks_app
from app.users.router import app as auth_app
from app.users.service import bootstrap_admin
from app.warehouse.router import app as warehouse_app

app = FastAPI(title="Soborbum")

# Applied at the root app, so it also covers requests routed into the mounted
# per-section sub-apps below (CORSMiddleware wraps the whole ASGI stack,
# including Mount dispatch) - the frontend only ever talks to this one origin.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    # Alembic owns schema management in normal operation (see entrypoint.sh);
    # create_all is a harmless no-op once migrations have run, and keeps a
    # fresh dev DB usable even before the first `alembic upgrade head`.
    if not inspect(engine).get_table_names():
        Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        bootstrap_admin(db)
    finally:
        db.close()


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(files_router)

app.mount("/api/auth", auth_app)
app.mount("/api/clients", clients_app)
app.mount("/api/production", production_app)
app.mount("/api/installation", installation_app)
app.mount("/api/cycles", cycle_app)
app.mount("/api/warehouse", warehouse_app)
app.mount("/api/marketing", marketing_app)
app.mount("/api/tasks", tasks_app)
app.mount("/api/ai", ai_app)
