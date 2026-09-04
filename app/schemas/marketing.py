from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import ContentStage
from app.schemas.files import FileAssetOut
from app.schemas.user import UserOut


class ContentItemCreate(BaseModel):
    title: str
    description: str | None = None
    planned_release_date: date | None = None
    platforms: list[str] = []
    assignee_ids: list[int] = []


class ContentItemUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    planned_release_date: date | None = None
    platforms: list[str] | None = None
    assignee_ids: list[int] | None = None


class ContentRawUpdate(BaseModel):
    raw_texts: str | None = None
    raw_file_ids: list[int] = []


class ContentFinalUpdate(BaseModel):
    final_texts: str | None = None
    final_file_ids: list[int] = []


class PostLinkIn(BaseModel):
    platform: str
    url: str


class ContentAnalysisUpdate(BaseModel):
    analysis_notes: str | None = None
    analysis_reach: dict[str, int] | None = None


class PostLinkOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    platform: str
    url: str


class ContentItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str | None
    planned_release_date: date | None
    platforms: list[str]
    stage: ContentStage
    created_at: datetime
    assignees: list[UserOut]

    raw_texts: str | None
    raw_files: list[FileAssetOut]
    raw_locked_at: datetime | None

    final_texts: str | None
    final_files: list[FileAssetOut]

    post_links: list[PostLinkOut]

    analysis_notes: str | None
    analysis_reach: dict | None

    @staticmethod
    def from_model(item) -> "ContentItemOut":
        return ContentItemOut(
            id=item.id,
            title=item.title,
            description=item.description,
            planned_release_date=item.planned_release_date,
            platforms=item.platforms,
            stage=item.stage,
            created_at=item.created_at,
            assignees=[UserOut.from_model(u) for u in item.assignees],
            raw_texts=item.raw_texts,
            raw_files=[FileAssetOut.model_validate(f) for f in item.raw_files],
            raw_locked_at=item.raw_locked_at,
            final_texts=item.final_texts,
            final_files=[FileAssetOut.model_validate(f) for f in item.final_files],
            post_links=[PostLinkOut.model_validate(p) for p in item.post_links],
            analysis_notes=item.analysis_notes,
            analysis_reach=item.analysis_reach,
        )
