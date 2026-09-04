"""Section "Совет директоров": a directed tree of strategic nodes (0 - the
whole company, 1 - business directions, 2 - sub-directions), plus the audit
trail of how each node got to its current state - either through an AI
council's proposal (app.board.council), a data-driven refresh
(app.board.actualize), or a plain manual edit.
"""

import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class BoardNodeColor(str, enum.Enum):
    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"


class BoardProposalStatus(str, enum.Enum):
    PENDING = "pending"      # council has spoken, waiting on the employee's decision
    APPLIED = "applied"      # accepted and cascaded through the tree
    CANCELLED = "cancelled"  # discarded without looping back for another round


class BoardChangeSource(str, enum.Enum):
    COUNCIL = "council"
    ACTUALIZE = "actualize"
    MANUAL = "manual"


class BoardChangeType(str, enum.Enum):
    CREATED = "created"
    UPDATED = "updated"
    DELETED = "deleted"


class BoardNode(Base):
    __tablename__ = "board_nodes"

    id: Mapped[int] = mapped_column(primary_key=True)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("board_nodes.id", ondelete="CASCADE"), nullable=True)
    level: Mapped[int] = mapped_column(Integer, nullable=False)  # 0 = предприятие, 1 = направление, 2 = поднаправление
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    color: Mapped[BoardNodeColor] = mapped_column(
        Enum(BoardNodeColor, name="board_node_color"), nullable=False, default=BoardNodeColor.GREEN
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    parent: Mapped["BoardNode | None"] = relationship(remote_side=[id], back_populates="children")
    children: Mapped[list["BoardNode"]] = relationship(
        back_populates="parent", cascade="all, delete-orphan", order_by="BoardNode.sort_order"
    )


class BoardProposal(Base):
    """One strategic-change discussion for a single node. `rounds` holds every
    pass of the council so far - the first entry is the original request, and
    each employee rejection-with-comment appends another (see
    app.board.council). Shape of one round:
    {"user_message": str, "council": [{"role": str, "role_label": str, "opinion": str}],
     "summary": str, "recommendation": "change"|"no_change", "proposed_title": str|None,
     "proposed_description": str|None, "proposed_color": str|None,
     "decision": "pending"|"accepted"|"rejected"}
    """

    __tablename__ = "board_proposals"

    id: Mapped[int] = mapped_column(primary_key=True)
    node_id: Mapped[int] = mapped_column(ForeignKey("board_nodes.id", ondelete="CASCADE"), nullable=False)
    requested_by_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[BoardProposalStatus] = mapped_column(
        Enum(BoardProposalStatus, name="board_proposal_status"), nullable=False, default=BoardProposalStatus.PENDING
    )
    rounds: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    node: Mapped["BoardNode"] = relationship()
    requested_by: Mapped["User"] = relationship()  # noqa: F821


class BoardNodeChange(Base):
    """Audit trail entry for one node touched by a council application, an
    actualize pass, or a manual edit. Deliberately not FK-constrained to
    board_nodes.id: a change record for a node that a later structural edit
    deleted must stay readable, so it can't cascade away with the node
    itself."""

    __tablename__ = "board_node_changes"

    id: Mapped[int] = mapped_column(primary_key=True)
    node_id: Mapped[int] = mapped_column(Integer, nullable=False)
    proposal_id: Mapped[int | None] = mapped_column(ForeignKey("board_proposals.id", ondelete="SET NULL"), nullable=True)
    source: Mapped[BoardChangeSource] = mapped_column(Enum(BoardChangeSource, name="board_change_source"), nullable=False)
    change_type: Mapped[BoardChangeType] = mapped_column(Enum(BoardChangeType, name="board_change_type"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    old_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    old_color: Mapped[str | None] = mapped_column(String(16), nullable=True)
    new_color: Mapped[str | None] = mapped_column(String(16), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    proposal: Mapped["BoardProposal | None"] = relationship()
    created_by: Mapped["User | None"] = relationship()  # noqa: F821
