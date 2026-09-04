import enum
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ClientStage(str, enum.Enum):
    LEAD = "lead"
    DISCUSSION = "discussion"
    APPROVAL = "approval"
    PAYMENT = "payment"
    POSTPAYMENT = "postpayment"


CLIENT_STAGE_ORDER = [
    ClientStage.LEAD,
    ClientStage.DISCUSSION,
    ClientStage.APPROVAL,
    ClientStage.PAYMENT,
    ClientStage.POSTPAYMENT,
]


class Client(Base):
    __tablename__ = "clients"

    id: Mapped[int] = mapped_column(primary_key=True)
    cycle_id: Mapped[int] = mapped_column(ForeignKey("cycles.id"), unique=True, nullable=False)
    stage: Mapped[ClientStage] = mapped_column(
        Enum(ClientStage, name="client_stage"), nullable=False, default=ClientStage.LEAD
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # --- Base info: required at creation, immutable forever after ---
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str] = mapped_column(String(32), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    inn: Mapped[str] = mapped_column(String(32), nullable=False)
    passport_number: Mapped[str] = mapped_column(String(64), nullable=False)
    birth_date: Mapped[date] = mapped_column(Date, nullable=False)

    # --- Project info: appears at DISCUSSION, required before APPROVAL, then locked ---
    wishes_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    estimated_price: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    house_area: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    layout_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    project_locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # --- Documents info: appears at APPROVAL, required before PAYMENT, then locked ---
    final_price: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    installation_address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    contract_file_id: Mapped[int | None] = mapped_column(ForeignKey("file_assets.id"), nullable=True)
    house_project_file_id: Mapped[int | None] = mapped_column(ForeignKey("file_assets.id"), nullable=True)
    documents_locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # --- Payment: appears at PAYMENT, required before POSTPAYMENT, then locked ---
    is_paid: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    payment_locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    cycle: Mapped["Cycle"] = relationship(back_populates="client")  # noqa: F821
    notes: Mapped[list["ClientNote"]] = relationship(back_populates="client", cascade="all, delete-orphan")
    contract_file: Mapped["FileAsset"] = relationship(foreign_keys=[contract_file_id])  # noqa: F821
    house_project_file: Mapped["FileAsset"] = relationship(foreign_keys=[house_project_file_id])  # noqa: F821


class ClientNote(Base):
    __tablename__ = "client_notes"

    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id", ondelete="CASCADE"), nullable=False)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    client: Mapped["Client"] = relationship(back_populates="notes")
    author: Mapped["User"] = relationship()  # noqa: F821
