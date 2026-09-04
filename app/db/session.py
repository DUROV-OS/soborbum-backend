import json

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

# default=str so JSON columns (e.g. ai_messages.tool_resolutions, which embeds
# raw tool-handler output like get_modules'/list_materials' created_at fields)
# don't blow up on datetimes - stdlib json.dumps has no idea how to serialize them.
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    json_serializer=lambda obj: json.dumps(obj, default=str, ensure_ascii=False),
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
