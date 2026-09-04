from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.warehouse.models import StockMovementReason


class WarehouseMaterialCreate(BaseModel):
    material_type: str
    size: str | None = None
    title: str
    supplier_name: str | None = None
    supplier_contact: str | None = None
    supplier_phone: str | None = None
    unit: str
    quantity_in_stock: float = 0
    threshold: float = 0


class WarehouseMaterialUpdate(BaseModel):
    material_type: str | None = None
    size: str | None = None
    title: str | None = None
    supplier_name: str | None = None
    supplier_contact: str | None = None
    supplier_phone: str | None = None
    threshold: float | None = None


class RequestBreakdownItem(BaseModel):
    module_id: int
    module_name: str
    production_id: int
    quantity_requested: float


class WarehouseMaterialOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    material_type: str
    size: str | None
    title: str
    supplier_name: str | None
    supplier_contact: str | None
    supplier_phone: str | None
    unit: str
    quantity_in_stock: float
    threshold: float
    total_requested: float
    needs_supply: bool
    request_breakdown: list[RequestBreakdownItem] = []
    created_at: datetime


class SupplyLineCreate(BaseModel):
    warehouse_material_id: int
    quantity: float


class SupplyCreate(BaseModel):
    supplier_name: str | None = None
    lines: list[SupplyLineCreate]


class SupplyLineOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    warehouse_material_id: int
    quantity: float


class SupplyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    supplier_name: str | None
    created_by_id: int
    created_at: datetime
    lines: list[SupplyLineOut] = []


class StockMovementOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    warehouse_material_id: int
    delta: float
    reason: StockMovementReason
    reference_id: int | None
    created_by_id: int
    created_at: datetime
