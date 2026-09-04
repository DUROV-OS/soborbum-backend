from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import FilePurpose


class FileAsset(Base):
    __tablename__ = "file_assets"

    id: Mapped[int] = mapped_column(primary_key=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(127), nullable=False)
    path_on_disk: Mapped[str] = mapped_column(String(500), nullable=False)
    purpose: Mapped[FilePurpose] = mapped_column(Enum(FilePurpose, name="file_purpose"), nullable=False)
    uploaded_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    uploaded_by: Mapped["User"] = relationship()  # noqa: F821
