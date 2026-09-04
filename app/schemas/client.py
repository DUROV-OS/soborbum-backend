from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import ClientStage
from app.schemas.files import FileAssetOut


class ClientCreate(BaseModel):
    full_name: str
    phone: str
    email: str
    inn: str
    passport_number: str
    birth_date: date


class ClientProjectUpdate(BaseModel):
    wishes_description: str | None = None
    estimated_price: float | None = None
    house_area: float | None = None
    layout_notes: str | None = None


class ClientDocumentsUpdate(BaseModel):
    final_price: float | None = None
    installation_address: str | None = None


class ClientPaymentUpdate(BaseModel):
    is_paid: bool


class ClientNoteCreate(BaseModel):
    text: str


class ClientNoteUpdate(BaseModel):
    text: str


class ClientNoteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    client_id: int
    author_id: int
    text: str
    created_at: datetime


class ClientOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    cycle_id: int
    stage: ClientStage
    created_at: datetime

    full_name: str
    phone: str
    email: str
    inn: str
    passport_number: str
    birth_date: date

    wishes_description: str | None
    estimated_price: float | None
    house_area: float | None
    layout_notes: str | None
    project_locked_at: datetime | None

    final_price: float | None
    installation_address: str | None
    contract_file: FileAssetOut | None
    house_project_file: FileAssetOut | None
    documents_locked_at: datetime | None

    is_paid: bool | None
    payment_locked_at: datetime | None

    notes: list[ClientNoteOut] = []
