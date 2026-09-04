import enum
from datetime import date, datetime

from sqlalchemy import Column, Date, DateTime, Enum, ForeignKey, JSON, String, Table, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ContentStage(str, enum.Enum):
    IDEA = "idea"
    GATHERING = "gathering"
    EDITING = "editing"
    RELEASE = "release"
    ANALYSIS = "analysis"


CONTENT_STAGE_ORDER = [
    ContentStage.IDEA,
    ContentStage.GATHERING,
    ContentStage.EDITING,
    ContentStage.RELEASE,
    ContentStage.ANALYSIS,
]

content_assignees = Table(
    "content_assignees",
    Base.metadata,
    Column("content_id", ForeignKey("content_items.id", ondelete="CASCADE"), primary_key=True),
    Column("user_id", ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
)

content_raw_files = Table(
    "content_raw_files",
    Base.metadata,
    Column("content_id", ForeignKey("content_items.id", ondelete="CASCADE"), primary_key=True),
    Column("file_id", ForeignKey("file_assets.id", ondelete="CASCADE"), primary_key=True),
)

content_final_files = Table(
    "content_final_files",
    Base.metadata,
    Column("content_id", ForeignKey("content_items.id", ondelete="CASCADE"), primary_key=True),
    Column("file_id", ForeignKey("file_assets.id", ondelete="CASCADE"), primary_key=True),
)


class ContentItem(Base):
    __tablename__ = "content_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    planned_release_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    platforms: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    stage: Mapped[ContentStage] = mapped_column(
        Enum(ContentStage, name="content_stage"), nullable=False, default=ContentStage.IDEA
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # raw material: appears at GATHERING, required before EDITING, then locked
    raw_texts: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # final material: appears at EDITING, required before RELEASE, always editable after
    final_texts: Mapped[str | None] = mapped_column(Text, nullable=True)

    # analysis: appears at ANALYSIS, always editable after
    analysis_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    analysis_reach: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    assignees: Mapped[list["User"]] = relationship(secondary=content_assignees)  # noqa: F821
    raw_files: Mapped[list["FileAsset"]] = relationship(secondary=content_raw_files)  # noqa: F821
    final_files: Mapped[list["FileAsset"]] = relationship(secondary=content_final_files)  # noqa: F821
    post_links: Mapped[list["PostLink"]] = relationship(back_populates="content", cascade="all, delete-orphan")


class PostLink(Base):
    __tablename__ = "post_links"

    id: Mapped[int] = mapped_column(primary_key=True)
    content_id: Mapped[int] = mapped_column(ForeignKey("content_items.id", ondelete="CASCADE"), nullable=False)
    platform: Mapped[str] = mapped_column(String(64), nullable=False)
    url: Mapped[str] = mapped_column(String(1000), nullable=False)

    content: Mapped["ContentItem"] = relationship(back_populates="post_links")
