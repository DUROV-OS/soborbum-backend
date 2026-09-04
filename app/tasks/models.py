import enum
from datetime import datetime

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, JSON, String, Table, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class TaskStatus(str, enum.Enum):
    NOT_READY = "not_ready"
    READY = "ready"
    IN_PROGRESS = "in_progress"
    IN_REVIEW = "in_review"
    DONE = "done"


class TaskLinkType(str, enum.Enum):
    """What auto-created this task, if anything. Domain sections that create
    linked tasks (clients, marketing, warehouse) look up their own entity by
    `Task.link_id` when a linked task is closed - see app/tasks/sync.py."""

    NONE = "none"
    CLIENT_STAGE = "client_stage"
    CONTENT_STAGE = "content_stage"
    WAREHOUSE_REQUEST = "warehouse_request"
    WAREHOUSE_SHORTAGE = "warehouse_shortage"


task_assignees = Table(
    "task_assignees",
    Base.metadata,
    Column("task_id", ForeignKey("tasks.id", ondelete="CASCADE"), primary_key=True),
    Column("user_id", ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
)

task_reviewers = Table(
    "task_reviewers",
    Base.metadata,
    Column("task_id", ForeignKey("tasks.id", ondelete="CASCADE"), primary_key=True),
    Column("user_id", ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
)

task_images = Table(
    "task_images",
    Base.metadata,
    Column("task_id", ForeignKey("tasks.id", ondelete="CASCADE"), primary_key=True),
    Column("file_id", ForeignKey("file_assets.id", ondelete="CASCADE"), primary_key=True),
)

task_dependencies = Table(
    "task_dependencies",
    Base.metadata,
    Column("task_id", ForeignKey("tasks.id", ondelete="CASCADE"), primary_key=True),
    Column("depends_on_id", ForeignKey("tasks.id", ondelete="CASCADE"), primary_key=True),
)


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus, name="task_status"), nullable=False, default=TaskStatus.NOT_READY
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Set when this task belongs to a production module - see app/production/models.py.
    module_id: Mapped[int | None] = mapped_column(ForeignKey("modules.id"), nullable=True)

    link_type: Mapped[TaskLinkType] = mapped_column(
        Enum(TaskLinkType, name="task_link_type"), nullable=False, default=TaskLinkType.NONE
    )
    link_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    link_meta: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    module: Mapped["ProductionModule"] = relationship(back_populates="tasks")  # noqa: F821

    assignees: Mapped[list["User"]] = relationship(secondary=task_assignees)  # noqa: F821
    reviewers: Mapped[list["User"]] = relationship(secondary=task_reviewers)  # noqa: F821
    images: Mapped[list["FileAsset"]] = relationship(secondary=task_images)  # noqa: F821

    depends_on: Mapped[list["Task"]] = relationship(
        secondary=task_dependencies,
        primaryjoin=id == task_dependencies.c.task_id,
        secondaryjoin=id == task_dependencies.c.depends_on_id,
        backref="blocks",
    )
