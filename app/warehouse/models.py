import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class StockMovementReason(str, enum.Enum):
    SUPPLY = "supply"
    ISSUED = "issued"
    REQUIRED_ADJUSTED_UP = "required_adjusted_up"
    REQUEST_REJECTED_RETURN = "request_rejected_return"
    MANUAL_ADJUST = "manual_adjust"


class WarehouseMaterial(Base):
    __tablename__ = "warehouse_materials"

    id: Mapped[int] = mapped_column(primary_key=True)

    # name group
    material_type: Mapped[str] = mapped_column(String(255), nullable=False)
    size: Mapped[str | None] = mapped_column(String(255), nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)

    # supplier group
    supplier_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    supplier_contact: Mapped[str | None] = mapped_column(String(255), nullable=True)
    supplier_phone: Mapped[str | None] = mapped_column(String(64), nullable=True)

    unit: Mapped[str] = mapped_column(String(32), nullable=False)
    quantity_in_stock: Mapped[float] = mapped_column(Numeric(14, 3, asdecimal=False), nullable=False, default=0)
    threshold: Mapped[float] = mapped_column(Numeric(14, 3, asdecimal=False), nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Supply(Base):
    __tablename__ = "supplies"

    id: Mapped[int] = mapped_column(primary_key=True)
    supplier_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    created_by: Mapped["User"] = relationship()  # noqa: F821
    lines: Mapped[list["SupplyLine"]] = relationship(back_populates="supply", cascade="all, delete-orphan")


class SupplyLine(Base):
    __tablename__ = "supply_lines"

    id: Mapped[int] = mapped_column(primary_key=True)
    supply_id: Mapped[int] = mapped_column(ForeignKey("supplies.id", ondelete="CASCADE"), nullable=False)
    warehouse_material_id: Mapped[int] = mapped_column(ForeignKey("warehouse_materials.id"), nullable=False)
    quantity: Mapped[float] = mapped_column(Numeric(14, 3, asdecimal=False), nullable=False)

    supply: Mapped["Supply"] = relationship(back_populates="lines")
    warehouse_material: Mapped["WarehouseMaterial"] = relationship()


class StockMovement(Base):
    __tablename__ = "stock_movements"

    id: Mapped[int] = mapped_column(primary_key=True)
    warehouse_material_id: Mapped[int] = mapped_column(ForeignKey("warehouse_materials.id"), nullable=False)
    delta: Mapped[float] = mapped_column(Numeric(14, 3, asdecimal=False), nullable=False)
    reason: Mapped[StockMovementReason] = mapped_column(
        Enum(StockMovementReason, name="stock_movement_reason"), nullable=False
    )
    reference_id: Mapped[int | None] = mapped_column(nullable=True)
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    warehouse_material: Mapped["WarehouseMaterial"] = relationship()
    created_by: Mapped["User"] = relationship()  # noqa: F821
