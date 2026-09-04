from sqlalchemy import Enum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import CycleStatus


class Cycle(Base):
    __tablename__ = "cycles"

    id: Mapped[int] = mapped_column(primary_key=True)
    status: Mapped[CycleStatus] = mapped_column(
        Enum(CycleStatus, name="cycle_status"), nullable=False, default=CycleStatus.CLIENT
    )

    client: Mapped["Client"] = relationship(back_populates="cycle", uselist=False)  # noqa: F821
    production: Mapped["Production"] = relationship(back_populates="cycle", uselist=False)  # noqa: F821
    installation: Mapped["Installation"] = relationship(back_populates="cycle", uselist=False)  # noqa: F821
