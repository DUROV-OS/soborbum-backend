from fastapi import Depends, FastAPI, HTTPException, UploadFile, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.common.module_access import Module as AccessModule
from app.core.deps import require_module
from app.db.session import get_db
from app.production.schemas import MaterialRequestOut
from app.users.models import User
from app.warehouse import excel, service as warehouse_service
from app.warehouse.models import StockMovementReason, Supply
from app.warehouse.schemas import (
    StockMovementOut,
    SupplyCreate,
    SupplyOut,
    WarehouseMaterialCreate,
    WarehouseMaterialOut,
    WarehouseMaterialUpdate,
)

app = FastAPI(
    title="Soborbum — Склад",
    description="Материалы, поставки, заявки от производства и история движения материалов.",
    version="1.0.0",
)

require_warehouse = require_module(AccessModule.WAREHOUSE)


@app.get("/materials", response_model=list[WarehouseMaterialOut])
def list_materials(
    db: Session = Depends(get_db),
    _: User = Depends(require_warehouse),
    needs_supply: bool | None = None,
):
    return warehouse_service.list_materials(db, only_needs_supply=bool(needs_supply))


@app.post("/materials", response_model=WarehouseMaterialOut, status_code=201)
def create_material(
    payload: WarehouseMaterialCreate, db: Session = Depends(get_db), _: User = Depends(require_warehouse)
):
    material = warehouse_service.create_material(db, payload)
    db.commit()
    return warehouse_service.to_out(db, material)


@app.get("/materials/{material_id}", response_model=WarehouseMaterialOut)
def get_material(material_id: int, db: Session = Depends(get_db), _: User = Depends(require_warehouse)):
    material = warehouse_service.get_material_or_404(db, material_id)
    return warehouse_service.to_out(db, material)


@app.patch("/materials/{material_id}", response_model=WarehouseMaterialOut)
def update_material(
    material_id: int,
    payload: WarehouseMaterialUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_warehouse),
):
    material = warehouse_service.get_material_or_404(db, material_id)
    material = warehouse_service.update_material(db, material, payload)
    db.commit()
    return warehouse_service.to_out(db, material)


@app.get("/materials/{material_id}/history", response_model=list[StockMovementOut])
def material_history(material_id: int, db: Session = Depends(get_db), _: User = Depends(require_warehouse)):
    warehouse_service.get_material_or_404(db, material_id)
    return warehouse_service.get_material_history(db, material_id)


@app.get("/history", response_model=list[StockMovementOut])
def history(
    db: Session = Depends(get_db),
    _: User = Depends(require_warehouse),
    material_id: int | None = None,
    reason: StockMovementReason | None = None,
):
    return warehouse_service.get_history(db, material_id=material_id, reason=reason)


@app.get("/supplies/template")
def download_supply_template(_: User = Depends(require_warehouse)):
    content = excel.generate_template()
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=supply_template.xlsx"},
    )


@app.post("/supplies", response_model=SupplyOut, status_code=201)
def create_supply(payload: SupplyCreate, db: Session = Depends(get_db), user: User = Depends(require_warehouse)):
    supply = warehouse_service.create_supply(db, payload, user)
    db.commit()
    db.refresh(supply)
    return supply


@app.post("/supplies/import", response_model=SupplyOut, status_code=201)
def import_supply(file: UploadFile, db: Session = Depends(get_db), user: User = Depends(require_warehouse)):
    rows = excel.parse_supply_rows(file)
    supply = warehouse_service.import_supply(db, rows, user)
    db.commit()
    db.refresh(supply)
    return supply


@app.get("/supplies/{supply_id}", response_model=SupplyOut)
def get_supply(supply_id: int, db: Session = Depends(get_db), _: User = Depends(require_warehouse)):
    supply = db.get(Supply, supply_id)
    if not supply:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Поставка не найдена")
    return supply


@app.post("/requests/{request_id}/approve", response_model=MaterialRequestOut)
def approve_request(request_id: int, db: Session = Depends(get_db), user: User = Depends(require_warehouse)):
    request = warehouse_service.get_request_or_404(db, request_id)
    request = warehouse_service.approve_request(db, request, user)
    db.commit()
    db.refresh(request)
    return request


@app.post("/requests/{request_id}/reject", response_model=MaterialRequestOut)
def reject_request(request_id: int, db: Session = Depends(get_db), user: User = Depends(require_warehouse)):
    request = warehouse_service.get_request_or_404(db, request_id)
    request = warehouse_service.reject_request(db, request, user)
    db.commit()
    db.refresh(request)
    return request
