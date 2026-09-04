import enum
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class InstallationStage(str, enum.Enum):
    DELIVERY = "delivery"
    INSTALLATION = "installation"
    FOLLOWUP = "followup"


INSTALLATION_STAGE_ORDER = [
    InstallationStage.DELIVERY,
    InstallationStage.INSTALLATION,
    InstallationStage.FOLLOWUP,
]


class Installation(Base):
    __tablename__ = "installations"

    id: Mapped[int] = mapped_column(primary_key=True)
    cycle_id: Mapped[int] = mapped_column(ForeignKey("cycles.id"), unique=True, nullable=False)
    stage: Mapped[InstallationStage] = mapped_column(
        Enum(InstallationStage, name="installation_stage"), nullable=False, default=InstallationStage.DELIVERY
    )
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    scheduled_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    cycle: Mapped["Cycle"] = relationship(back_populates="installation")  # noqa: F821
