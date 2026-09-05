import enum

from sqlalchemy import Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class CycleStatus(str, enum.Enum):
    CLIENT = "client"
    PRODUCTION = "production"
    INSTALLATION = "installation"
    COMPLETED = "completed"


class Cycle(Base):
    __tablename__ = "cycles"

    id: Mapped[int] = mapped_column(primary_key=True)
    status: Mapped[CycleStatus] = mapped_column(
        Enum(CycleStatus, name="cycle_status"), nullable=False, default=CycleStatus.CLIENT
    )

    client: Mapped["Client"] = relationship(back_populates="cycle", uselist=False)  # noqa: F821
    # One цикл can now hold several дома in production (множественный заказ) —
    # one Production project per дом, ordered by house_index.
    productions: Mapped[list["Production"]] = relationship(  # noqa: F821
        back_populates="cycle",
        cascade="all, delete-orphan",
        order_by="Production.house_index",
    )
    installation: Mapped["Installation"] = relationship(back_populates="cycle", uselist=False)  # noqa: F821

    @property
    def production(self) -> "Production | None":  # noqa: F821
        """Backwards-compatible accessor for the first (or only) дом's project."""
        return self.productions[0] if self.productions else None
