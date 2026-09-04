from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.common.module_access import Module as AccessModule
from app.production.models import MaterialRequest, MaterialRequestStatus, ModuleMaterial, ProductionModule
from app.tasks import service as task_service
from app.tasks.models import Task, TaskLinkType, TaskStatus
from app.users import service as user_service
from app.users.models import User
from app.warehouse.models import (
    StockMovement,
    StockMovementReason,
    Supply,
    SupplyLine,
    Warehouse,
    WarehouseMaterial,
)
from app.warehouse.schemas import (
    RequestBreakdownItem,
    SupplyCreate,
    WarehouseMaterialCreate,
    WarehouseMaterialOut,
    WarehouseMaterialUpdate,
)


def get_material_or_404(db: Session, material_id: int) -> WarehouseMaterial:
    material = db.get(WarehouseMaterial, material_id)
    if not material:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Материал не найден")
    return material


def get_request_or_404(db: Session, request_id: int) -> MaterialRequest:
    request = db.get(MaterialRequest, request_id)
    if not request:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Заявка на материал не найдена")
    return request


def create_material(db: Session, payload: WarehouseMaterialCreate) -> WarehouseMaterial:
    material = WarehouseMaterial(**payload.model_dump())
    db.add(material)
    db.flush()
    sync_shortage_task(db, material)
    return material


def update_material(db: Session, material: WarehouseMaterial, payload: WarehouseMaterialUpdate) -> WarehouseMaterial:
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(material, field, value)
    db.flush()
    sync_shortage_task(db, material)
    return material


def compute_breakdown(db: Session, material_id: int) -> list[RequestBreakdownItem]:
    rows = (
        db.query(ModuleMaterial.module_id, ProductionModule.name, ProductionModule.production_id, MaterialRequest.quantity)
        .join(MaterialRequest, MaterialRequest.module_material_id == ModuleMaterial.id)
        .join(ProductionModule, ProductionModule.id == ModuleMaterial.module_id)
        .filter(
            MaterialRequest.warehouse_material_id == material_id,
            MaterialRequest.status == MaterialRequestStatus.PENDING,
        )
        .all()
    )
    breakdown: dict[int, RequestBreakdownItem] = {}
    for module_id, module_name, production_id, quantity in rows:
        if module_id in breakdown:
            breakdown[module_id].quantity_requested += float(quantity)
        else:
            breakdown[module_id] = RequestBreakdownItem(
                module_id=module_id,
                module_name=module_name,
                production_id=production_id,
                quantity_requested=float(quantity),
            )
    return list(breakdown.values())


def total_requested(db: Session, material_id: int) -> float:
    return sum(item.quantity_requested for item in compute_breakdown(db, material_id))


def needs_supply(material: WarehouseMaterial, requested: float) -> bool:
    return (float(material.quantity_in_stock) - requested) < float(material.threshold)


def to_out(db: Session, material: WarehouseMaterial) -> WarehouseMaterialOut:
    breakdown = compute_breakdown(db, material.id)
    requested = sum(item.quantity_requested for item in breakdown)
    return WarehouseMaterialOut(
        id=material.id,
        warehouse=material.warehouse,
        category=material.category,
        title=material.title,
        code=material.code,
        unit=material.unit,
        is_fractional=material.is_fractional,
        quantity_in_stock=float(material.quantity_in_stock),
        purchase_price=float(material.purchase_price),
        threshold=float(material.threshold),
        total_requested=requested,
        needs_supply=needs_supply(material, requested),
        request_breakdown=breakdown,
        created_at=material.created_at,
    )


def list_materials(
    db: Session, only_needs_supply: bool = False, warehouse: Warehouse | None = None
) -> list[WarehouseMaterialOut]:
    query = db.query(WarehouseMaterial)
    if warehouse is not None:
        query = query.filter(WarehouseMaterial.warehouse == warehouse)
    materials = query.order_by(WarehouseMaterial.id).all()
    result = [to_out(db, m) for m in materials]
    if only_needs_supply:
        result = [r for r in result if r.needs_supply]
    return result


SHORTAGE_TITLE = "Заказать дефицитный материал: {title}"


def sync_shortage_task(db: Session, material: WarehouseMaterial) -> None:
    requested = total_requested(db, material.id)
    open_task = (
        db.query(Task)
        .filter(
            Task.link_type == TaskLinkType.WAREHOUSE_SHORTAGE,
            Task.link_id == material.id,
            Task.status != TaskStatus.DONE,
        )
        .first()
    )
    if needs_supply(material, requested):
        if not open_task:
            assignees = user_service.users_with_access(db, AccessModule.WAREHOUSE)
            task_service.create_link_task(
                db,
                title=SHORTAGE_TITLE.format(title=material.title),
                link_type=TaskLinkType.WAREHOUSE_SHORTAGE,
                link_id=material.id,
                assignees=assignees,
            )
    else:
        if open_task:
            task_service.force_close(db, open_task)


def log_movement(
    db: Session,
    material: WarehouseMaterial,
    delta: float,
    reason: StockMovementReason,
    created_by: User,
    reference_id: int | None = None,
) -> StockMovement:
    movement = StockMovement(
        warehouse_material_id=material.id,
        delta=delta,
        reason=reason,
        reference_id=reference_id,
        created_by_id=created_by.id,
    )
    db.add(movement)
    db.flush()
    return movement


def approve_request(db: Session, request: MaterialRequest, decided_by: User) -> MaterialRequest:
    if request.status != MaterialRequestStatus.PENDING:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Заявка уже обработана")

    module_material = request.module_material
    warehouse_material = request.warehouse_material

    module_material.quantity_requested -= request.quantity
    module_material.quantity_provided += request.quantity
    warehouse_material.quantity_in_stock -= request.quantity

    request.status = MaterialRequestStatus.APPROVED
    request.decided_by_id = decided_by.id
    request.decided_at = datetime.now(timezone.utc)
    db.flush()

    log_movement(db, warehouse_material, -float(request.quantity), StockMovementReason.ISSUED, decided_by, request.id)

    if request.task_id:
        task = db.get(Task, request.task_id)
        if task:
            task_service.force_close(db, task)

    sync_shortage_task(db, warehouse_material)
    return request


def reject_request(db: Session, request: MaterialRequest, decided_by: User) -> MaterialRequest:
    if request.status != MaterialRequestStatus.PENDING:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Заявка уже обработана")

    module_material = request.module_material
    warehouse_material = request.warehouse_material

    module_material.quantity_requested -= request.quantity
    module_material.quantity_required += request.quantity

    request.status = MaterialRequestStatus.REJECTED
    request.decided_by_id = decided_by.id
    request.decided_at = datetime.now(timezone.utc)
    db.flush()

    log_movement(db, warehouse_material, 0, StockMovementReason.REQUEST_REJECTED_RETURN, decided_by, request.id)

    if request.task_id:
        task = db.get(Task, request.task_id)
        if task:
            task_service.force_close(db, task)

    sync_shortage_task(db, warehouse_material)
    return request


def create_supply(db: Session, payload: SupplyCreate, created_by: User) -> Supply:
    materials = {line.warehouse_material_id: get_material_or_404(db, line.warehouse_material_id) for line in payload.lines}
    warehouses = {m.warehouse for m in materials.values()}
    if len(warehouses) > 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Поставка должна ссылаться на материалы только одного склада",
        )

    supply = Supply(supplier_name=payload.supplier_name, created_by_id=created_by.id)
    db.add(supply)
    db.flush()

    for line in payload.lines:
        material = materials[line.warehouse_material_id]
        db.add(SupplyLine(supply_id=supply.id, warehouse_material_id=material.id, quantity=line.quantity))
        material.quantity_in_stock += line.quantity
        db.flush()
        log_movement(db, material, float(line.quantity), StockMovementReason.SUPPLY, created_by, supply.id)
        sync_shortage_task(db, material)

    db.flush()
    return supply


def import_supply(db: Session, rows: list[dict], warehouse: Warehouse, created_by: User) -> Supply:
    supply = Supply(supplier_name=None, created_by_id=created_by.id)
    db.add(supply)
    db.flush()

    for row in rows:
        material: WarehouseMaterial | None = None
        if row["warehouse_material_id"] is not None:
            material = get_material_or_404(db, row["warehouse_material_id"])
            if material.warehouse != warehouse:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Материал «{material.title}» принадлежит другому складу",
                )
        else:
            material = (
                db.query(WarehouseMaterial)
                .filter_by(warehouse=warehouse, code=row["code"])
                .first()
            )
            if material is None:
                if not row["unit"]:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Для нового материала «{row['title']}» нужно указать единицу измерения",
                    )
                material = WarehouseMaterial(
                    warehouse=warehouse,
                    category=row["category"],
                    code=row["code"],
                    title=row["title"],
                    unit=row["unit"],
                    is_fractional=row["is_fractional"],
                    purchase_price=row["purchase_price"],
                    quantity_in_stock=0,
                    threshold=0,
                )
                db.add(material)
                db.flush()

        db.add(SupplyLine(supply_id=supply.id, warehouse_material_id=material.id, quantity=row["quantity"]))
        material.quantity_in_stock += row["quantity"]
        db.flush()
        log_movement(db, material, float(row["quantity"]), StockMovementReason.SUPPLY, created_by, supply.id)
        sync_shortage_task(db, material)

    db.flush()
    return supply


def get_material_history(db: Session, material_id: int) -> list[StockMovement]:
    return (
        db.query(StockMovement)
        .filter(StockMovement.warehouse_material_id == material_id)
        .order_by(StockMovement.created_at.desc())
        .all()
    )


def get_history(
    db: Session,
    material_id: int | None = None,
    reason: StockMovementReason | None = None,
) -> list[StockMovement]:
    query = db.query(StockMovement)
    if material_id is not None:
        query = query.filter(StockMovement.warehouse_material_id == material_id)
    if reason is not None:
        query = query.filter(StockMovement.reason == reason)
    return query.order_by(StockMovement.created_at.desc()).all()
