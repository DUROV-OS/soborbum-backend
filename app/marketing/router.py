from datetime import date

from fastapi import Depends, FastAPI
from sqlalchemy.orm import Session

from app.common.module_access import Module as AccessModule
from app.core.deps import require_module
from app.db.session import get_db
from app.marketing import service as marketing_service
from app.marketing.schemas import (
    ContentAnalysisUpdate,
    ContentFinalUpdate,
    ContentItemCreate,
    ContentItemOut,
    ContentItemUpdate,
    ContentRawUpdate,
    PostLinkIn,
)
from app.users.models import User

app = FastAPI(
    title="Soborbum — Маркетинг",
    description="Календарь выпуска контента: от идеи до анализа результатов.",
    version="1.0.0",
)

require_marketing = require_module(AccessModule.MARKETING)


@app.get("/calendar", response_model=list[ContentItemOut])
def calendar(
    db: Session = Depends(get_db),
    _: User = Depends(require_marketing),
    date_from: date | None = None,
    date_to: date | None = None,
):
    items = marketing_service.get_calendar(db, date_from, date_to)
    return [ContentItemOut.from_model(i) for i in items]


@app.post("/content", response_model=ContentItemOut, status_code=201)
def create_content(payload: ContentItemCreate, db: Session = Depends(get_db), _: User = Depends(require_marketing)):
    content = marketing_service.create_content(db, payload)
    db.commit()
    db.refresh(content)
    return ContentItemOut.from_model(content)


@app.get("/content/{content_id}", response_model=ContentItemOut)
def get_content(content_id: int, db: Session = Depends(get_db), _: User = Depends(require_marketing)):
    content = marketing_service.get_content_or_404(db, content_id)
    return ContentItemOut.from_model(content)


@app.patch("/content/{content_id}", response_model=ContentItemOut)
def update_content(
    content_id: int,
    payload: ContentItemUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_marketing),
):
    content = marketing_service.get_content_or_404(db, content_id)
    content = marketing_service.update_basic(db, content, payload)
    db.commit()
    db.refresh(content)
    return ContentItemOut.from_model(content)


@app.patch("/content/{content_id}/raw", response_model=ContentItemOut)
def update_raw(
    content_id: int,
    payload: ContentRawUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_marketing),
):
    content = marketing_service.get_content_or_404(db, content_id)
    content = marketing_service.update_raw(db, content, payload)
    db.commit()
    db.refresh(content)
    return ContentItemOut.from_model(content)


@app.patch("/content/{content_id}/final", response_model=ContentItemOut)
def update_final(
    content_id: int,
    payload: ContentFinalUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_marketing),
):
    content = marketing_service.get_content_or_404(db, content_id)
    content = marketing_service.update_final(db, content, payload)
    db.commit()
    db.refresh(content)
    return ContentItemOut.from_model(content)


@app.put("/content/{content_id}/post-links", response_model=ContentItemOut)
def set_post_links(
    content_id: int,
    payload: list[PostLinkIn],
    db: Session = Depends(get_db),
    _: User = Depends(require_marketing),
):
    content = marketing_service.get_content_or_404(db, content_id)
    content = marketing_service.set_post_links(db, content, payload)
    db.commit()
    db.refresh(content)
    return ContentItemOut.from_model(content)


@app.patch("/content/{content_id}/analysis", response_model=ContentItemOut)
def update_analysis(
    content_id: int,
    payload: ContentAnalysisUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_marketing),
):
    content = marketing_service.get_content_or_404(db, content_id)
    content = marketing_service.update_analysis(db, content, payload)
    db.commit()
    db.refresh(content)
    return ContentItemOut.from_model(content)


@app.post("/content/{content_id}/transition", response_model=ContentItemOut)
def transition_content(content_id: int, db: Session = Depends(get_db), _: User = Depends(require_marketing)):
    content = marketing_service.get_content_or_404(db, content_id)
    content = marketing_service.transition_stage(db, content)
    db.commit()
    db.refresh(content)
    return ContentItemOut.from_model(content)
