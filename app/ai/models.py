import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ChatDomain(str, enum.Enum):
    CLIENTS = "clients"
    PRODUCTION = "production"
    CYCLE = "cycle"
    WAREHOUSE = "warehouse"
    MARKETING = "marketing"
    TASKS = "tasks"
    GENERAL = "general"


class ChatMode(str, enum.Enum):
    NO_ACTIONS = "no_actions"
    REQUIRE_APPROVAL = "require_approval"
    AUTO_APPROVE = "auto_approve"


class PendingActionStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class Chat(Base):
    __tablename__ = "ai_chats"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    domain: Mapped[ChatDomain] = mapped_column(Enum(ChatDomain, name="ai_chat_domain"), nullable=False)
    mode: Mapped[ChatMode] = mapped_column(
        Enum(ChatMode, name="ai_chat_mode"), nullable=False, default=ChatMode.REQUIRE_APPROVAL
    )
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    owner: Mapped["User"] = relationship()  # noqa: F821
    messages: Mapped[list["Message"]] = relationship(
        back_populates="chat", cascade="all, delete-orphan", order_by="Message.id"
    )


class Message(Base):
    __tablename__ = "ai_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    chat_id: Mapped[int] = mapped_column(ForeignKey("ai_chats.id", ondelete="CASCADE"), nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False)  # "user" | "assistant" (Anthropic wire format)
    content: Mapped[list] = mapped_column(JSON, nullable=False)
    tool_resolutions: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    chat: Mapped["Chat"] = relationship(back_populates="messages")


class PendingAction(Base):
    __tablename__ = "ai_pending_actions"

    id: Mapped[int] = mapped_column(primary_key=True)
    chat_id: Mapped[int] = mapped_column(ForeignKey("ai_chats.id", ondelete="CASCADE"), nullable=False)
    message_id: Mapped[int] = mapped_column(ForeignKey("ai_messages.id", ondelete="CASCADE"), nullable=False)
    tool_use_id: Mapped[str] = mapped_column(String(128), nullable=False)
    tool_name: Mapped[str] = mapped_column(String(128), nullable=False)
    tool_input: Mapped[dict] = mapped_column(JSON, nullable=False)
    status: Mapped[PendingActionStatus] = mapped_column(
        Enum(PendingActionStatus, name="ai_pending_action_status"),
        nullable=False,
        default=PendingActionStatus.PENDING,
    )
    decided_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    chat: Mapped["Chat"] = relationship()
    message: Mapped["Message"] = relationship()
    decided_by: Mapped["User"] = relationship()  # noqa: F821


class McpCredential(Base):
    """Singleton row (id=1) holding the tokens from the one-time interactive
    OAuth authorization against the knowledge-base MCP server - see
    app/ai/mcp_auth.py. There is one shared connection to the knowledge base
    for the whole system, not one per employee."""

    __tablename__ = "ai_mcp_credentials"

    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    access_token: Mapped[str] = mapped_column(String(4096), nullable=False)
    refresh_token: Mapped[str | None] = mapped_column(String(4096), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
