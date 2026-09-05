from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.clients.models import CLIENT_STAGE_ORDER, Client, ClientNote, ClientStage, OrderType
from app.clients.schemas import ClientCreate, ClientDocumentsUpdate, ClientPaymentUpdate, ClientProjectUpdate
from app.common.module_access import Module
from app.cycle.models import Cycle, CycleStatus
from app.tasks import service as task_service
from app.tasks import sync as task_sync
from app.tasks.models import TaskLinkType
from app.users import service as user_service


def _next_stage(stage: ClientStage) -> ClientStage | None:
    idx = CLIENT_STAGE_ORDER.index(stage)
    if idx + 1 < len(CLIENT_STAGE_ORDER):
        return CLIENT_STAGE_ORDER[idx + 1]
    return None


def _create_transition_task(db: Session, client: Client) -> None:
    if _next_stage(client.stage) is None:
        return
    assignees = user_service.users_with_access(db, Module.CLIENTS)
    task_service.create_link_task(
        db,
        title=f"Клиент «{client.full_name}»: перевести со стадии «{client.stage.value}» на следующую",
        link_type=TaskLinkType.CLIENT_STAGE,
        link_id=client.id,
        assignees=assignees,
        link_meta={"stage": client.stage.value},
    )


def create_client(db: Session, payload: ClientCreate) -> Client:
    cycle = Cycle(status=CycleStatus.CLIENT)
    db.add(cycle)
    db.flush()

    client = Client(
        cycle_id=cycle.id,
        full_name=payload.full_name,
        phone=payload.phone,
        email=payload.email,
        contacts=[c.model_dump() for c in payload.contacts],
    )
    db.add(client)
    db.flush()

    _create_transition_task(db, client)
    return client


def get_client_or_404(db: Session, client_id: int) -> Client:
    client = db.get(Client, client_id)
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Клиент не найден")
    return client


def update_project(db: Session, client: Client, payload: ClientProjectUpdate) -> Client:
    if client.project_locked_at is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Проектные данные уже зафиксированы")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(client, field, value)
    db.flush()
    return client


def update_documents(db: Session, client: Client, payload: ClientDocumentsUpdate) -> Client:
    if client.documents_locked_at is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Документные данные уже зафиксированы")
    data = payload.model_dump(exclude_unset=True)
    if "houses_count" in data and data["houses_count"] is not None:
        count = data["houses_count"]
        if count < 1:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Количество домов не может быть меньше 1")
        if client.order_type != OrderType.MULTIPLE and count != 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Количество домов > 1 доступно только для множественного заказа",
            )
    for field, value in data.items():
        setattr(client, field, value)
    db.flush()
    return client


def update_payment(db: Session, client: Client, payload: ClientPaymentUpdate) -> Client:
    if client.payment_locked_at is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Статус оплаты уже зафиксирован")
    client.is_paid = payload.is_paid
    db.flush()
    return client


def set_contract_file(db: Session, client: Client, file_id: int) -> Client:
    if client.documents_locked_at is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Документные данные уже зафиксированы")
    client.contract_file_id = file_id
    db.flush()
    return client


def set_house_project_file(db: Session, client: Client, file_id: int) -> Client:
    if client.documents_locked_at is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Документные данные уже зафиксированы")
    client.house_project_file_id = file_id
    db.flush()
    return client


def add_note(db: Session, client: Client, author_id: int, text: str) -> ClientNote:
    note = ClientNote(client_id=client.id, author_id=author_id, text=text)
    db.add(note)
    db.flush()
    return note


def update_note(db: Session, note: ClientNote, text: str) -> ClientNote:
    note.text = text
    db.flush()
    return note


def delete_note(db: Session, note: ClientNote) -> None:
    db.delete(note)
    db.flush()


_PROJECT_REQUIRED = ["order_type", "wishes_description", "estimated_price", "house_area", "layout_notes"]
_DOCUMENTS_REQUIRED = ["final_price", "installation_address", "contract_file_id", "house_project_file_id"]


def transition_stage(db: Session, client: Client) -> Client:
    next_stage = _next_stage(client.stage)
    if next_stage is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Клиент уже на последней стадии")

    if client.stage == ClientStage.DISCUSSION:
        missing = [f for f in _PROJECT_REQUIRED if getattr(client, f) is None]
        if missing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Не заполнены проектные поля: {', '.join(missing)}",
            )
        client.project_locked_at = datetime.now(timezone.utc)

    elif client.stage == ClientStage.APPROVAL:
        missing = [f for f in _DOCUMENTS_REQUIRED if getattr(client, f) is None]
        if missing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Не заполнены документные поля: {', '.join(missing)}",
            )
        if client.order_type == OrderType.SINGLE:
            client.houses_count = 1
        elif client.order_type == OrderType.MULTIPLE and client.houses_count < 2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Для множественного заказа укажите количество домов (не меньше 2)",
            )
        client.documents_locked_at = datetime.now(timezone.utc)

    elif client.stage == ClientStage.PAYMENT:
        if client.is_paid is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Не указан статус оплаты")
        client.payment_locked_at = datetime.now(timezone.utc)

    client.stage = next_stage
    db.flush()

    if next_stage == ClientStage.POSTPAYMENT:
        from app.production.models import Production

        houses = client.houses_count if client.order_type == OrderType.MULTIPLE else 1
        for i in range(1, houses + 1):
            db.add(
                Production(
                    cycle_id=client.cycle_id,
                    house_index=i,
                    name=f"Дом {i}" if houses > 1 else "Дом",
                )
            )
        client.cycle.status = CycleStatus.PRODUCTION
        db.flush()

    task_service.close_open_link_task(db, TaskLinkType.CLIENT_STAGE, client.id)
    _create_transition_task(db, client)

    return client


@task_sync.register(TaskLinkType.CLIENT_STAGE)
def _on_client_task_closed(db: Session, task) -> None:
    client = db.get(Client, task.link_id)
    if client is not None:
        transition_stage(db, client)
