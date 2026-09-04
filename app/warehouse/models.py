import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class StockMovementReason(str, enum.Enum):
    SUPPLY = "supply"
    ISSUED = "issued"
    REQUIRED_ADJUSTED_UP = "required_adjusted_up"
    REQUEST_REJECTED_RETURN = "request_rejected_return"
    MANUAL_ADJUST = "manual_adjust"


class Warehouse(str, enum.Enum):
    TECHNOLOGY = "Склад Технология"
    ID_GROUP = "Склад ИД Групп"


class MaterialCategory(str, enum.Enum):
    NONE = "без категории"
    BEAMS_BOARDS = "брусы/доска"
    VENTILATION = "вентиляция"
    WATER_SEWAGE = "вода/канализация"
    TOOLS = "инструмент"
    ASSEMBLY_KITS = "комплекты для сборки"
    PAINT_VARNISH_OIL = "краска/лак/масло"
    ROOFING = "кровельный материал"
    FURNITURE = "мебель"
    MEMBRANE = "мембрана"
    FASTENERS = "метизы"
    WINDOWS_DOORS = "окна и двери"
    STOVE = "печное"
    CONSUMABLES = "расходные материалы"
    PILES = "сваи"
    INSULATION = "утепление и изоляции"
    UTILITY_BLOCK = "хоз.блок"
    TANKS = "чаны"
    ELECTRICAL = "электрика"


class WarehouseMaterial(Base):
    __tablename__ = "warehouse_materials"
    __table_args__ = (UniqueConstraint("warehouse", "code", name="uq_warehouse_materials_warehouse_code"),)

    id: Mapped[int] = mapped_column(primary_key=True)

    # each warehouse keeps its own materials ledger - code is unique per warehouse, not globally
    #
    # values_callable: the underlying postgres enum type stores the Russian
    # label (member .value), not the python member .name - it's what the
    # migration's CREATE TYPE lists and what the API sends/receives as JSON.
    warehouse: Mapped[Warehouse] = mapped_column(
        Enum(Warehouse, name="warehouse_name", values_callable=lambda enum_cls: [e.value for e in enum_cls]),
        nullable=False,
    )
    category: Mapped[MaterialCategory] = mapped_column(
        Enum(MaterialCategory, name="material_category", values_callable=lambda enum_cls: [e.value for e in enum_cls]),
        nullable=False,
        default=MaterialCategory.NONE,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(64), nullable=False)

    unit: Mapped[str] = mapped_column(String(32), nullable=False)
    is_fractional: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    quantity_in_stock: Mapped[float] = mapped_column(Numeric(14, 3, asdecimal=False), nullable=False, default=0)
    purchase_price: Mapped[float] = mapped_column(Numeric(14, 2, asdecimal=False), nullable=False, default=0)

    # kept for the automatic shortage-task feature (see service.sync_shortage_task);
    # not part of the user-facing field set, edited only via update_threshold
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
