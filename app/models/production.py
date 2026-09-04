from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import MaterialRequestStatus


class Production(Base):
    __tablename__ = "productions"

    id: Mapped[int] = mapped_column(primary_key=True)
    cycle_id: Mapped[int] = mapped_column(ForeignKey("cycles.id"), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    cycle: Mapped["Cycle"] = relationship(back_populates="production")  # noqa: F821
    modules: Mapped[list["Module"]] = relationship(back_populates="production", cascade="all, delete-orphan")


class Module(Base):
    __tablename__ = "modules"

    id: Mapped[int] = mapped_column(primary_key=True)
    production_id: Mapped[int] = mapped_column(ForeignKey("productions.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    production: Mapped["Production"] = relationship(back_populates="modules")
    materials: Mapped[list["ModuleMaterial"]] = relationship(back_populates="module", cascade="all, delete-orphan")
    tasks: Mapped[list["Task"]] = relationship(back_populates="module")  # noqa: F821


class ModuleMaterial(Base):
    __tablename__ = "module_materials"

    id: Mapped[int] = mapped_column(primary_key=True)
    module_id: Mapped[int] = mapped_column(ForeignKey("modules.id", ondelete="CASCADE"), nullable=False)
    warehouse_material_id: Mapped[int] = mapped_column(ForeignKey("warehouse_materials.id"), nullable=False)
    inventory_number: Mapped[str] = mapped_column(String(64), nullable=False)
    unit: Mapped[str] = mapped_column(String(32), nullable=False)
    quantity_required: Mapped[float] = mapped_column(Numeric(14, 3), nullable=False, default=0)
    quantity_requested: Mapped[float] = mapped_column(Numeric(14, 3), nullable=False, default=0)
    quantity_provided: Mapped[float] = mapped_column(Numeric(14, 3), nullable=False, default=0)

    module: Mapped["Module"] = relationship(back_populates="materials")
    warehouse_material: Mapped["WarehouseMaterial"] = relationship()  # noqa: F821
    requests: Mapped[list["MaterialRequest"]] = relationship(
        back_populates="module_material", cascade="all, delete-orphan"
    )


class MaterialRequest(Base):
    __tablename__ = "material_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    module_material_id: Mapped[int] = mapped_column(
        ForeignKey("module_materials.id", ondelete="CASCADE"), nullable=False
    )
    warehouse_material_id: Mapped[int] = mapped_column(ForeignKey("warehouse_materials.id"), nullable=False)
    quantity: Mapped[float] = mapped_column(Numeric(14, 3), nullable=False)
    status: Mapped[MaterialRequestStatus] = mapped_column(
        Enum(MaterialRequestStatus, name="material_request_status"),
        nullable=False,
        default=MaterialRequestStatus.PENDING,
    )
    requested_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    decided_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    task_id: Mapped[int | None] = mapped_column(ForeignKey("tasks.id"), nullable=True)

    module_material: Mapped["ModuleMaterial"] = relationship(back_populates="requests")
    warehouse_material: Mapped["WarehouseMaterial"] = relationship()  # noqa: F821
    requested_by: Mapped["User"] = relationship(foreign_keys=[requested_by_id])  # noqa: F821
    decided_by: Mapped["User"] = relationship(foreign_keys=[decided_by_id])  # noqa: F821
