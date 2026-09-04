from datetime import datetime, timezone

from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy.orm import Session

from app.board import actualize as board_actualize
from app.board import council as board_council
from app.board import service as board_service
from app.board.models import BoardNodeChange, BoardProposalStatus
from app.board.schemas import (
    ActualizeResultOut,
    ApplyResultOut,
    BoardNodeChangeOut,
    BoardNodeDetailOut,
    BoardNodeOut,
    BoardNodeUpdate,
    BoardProposalOut,
    ProposalDecisionRequest,
    ProposeChangeRequest,
)
from app.common.module_access import Module
from app.core.deps import require_admin, require_module
from app.db.session import get_db
from app.users.models import User

app = FastAPI(
    title="Soborbum — Совет директоров",
    description="Дерево стратегических направлений компании: описание, статус критичности по каждой "
    "ветке, и ИИ-совет из нескольких ролей, который обсуждает и проводит стратегические изменения по дереву.",
    version="0.1",
)

require_board = require_module(Module.BOARD)


@app.get("/tree", response_model=BoardNodeOut)
def get_tree(db: Session = Depends(get_db), _: User = Depends(require_board)):
    root = board_service.get_root(db)
    if root is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Дерево ещё не создано")
    return BoardNodeOut.from_model(root)


@app.get("/nodes/{node_id}", response_model=BoardNodeDetailOut)
def get_node(node_id: int, db: Session = Depends(get_db), _: User = Depends(require_board)):
    node = board_service.get_node_or_404(db, node_id)
    return BoardNodeDetailOut.from_model_with_path(node, board_service.node_path(node))


@app.patch("/nodes/{node_id}", response_model=BoardNodeDetailOut)
def update_node(
    node_id: int, payload: BoardNodeUpdate, db: Session = Depends(get_db), user: User = Depends(require_board)
):
    node = board_service.get_node_or_404(db, node_id)
    node = board_service.update_node_manual(db, node, payload.title, payload.description, payload.color, user)
    return BoardNodeDetailOut.from_model_with_path(node, board_service.node_path(node))


@app.get("/nodes/{node_id}/changes", response_model=list[BoardNodeChangeOut])
def node_change_history(node_id: int, db: Session = Depends(get_db), _: User = Depends(require_board)):
    board_service.get_node_or_404(db, node_id)  # 404 if the node never existed
    return (
        db.query(BoardNodeChange)
        .filter(BoardNodeChange.node_id == node_id)
        .order_by(BoardNodeChange.id.desc())
        .all()
    )


@app.post("/nodes/{node_id}/propose", response_model=BoardProposalOut)
def propose_change(
    node_id: int,
    payload: ProposeChangeRequest,
    include_transcript: bool = False,
    db: Session = Depends(get_db),
    user: User = Depends(require_board),
):
    """Stage 1: convenes the council (7 roles + synthesis) over one node and
    stores its conclusion as a pending proposal, for the employee to accept
    or reject via POST /proposals/{id}/respond."""
    node = board_service.get_node_or_404(db, node_id)
    proposal = board_council.propose_change(db, node, user, payload.message)
    return BoardProposalOut.from_model(proposal, include_transcript)


@app.get("/proposals", response_model=list[BoardProposalOut])
def list_proposals(
    node_id: int | None = None,
    proposal_status: BoardProposalStatus | None = None,
    include_transcript: bool = False,
    db: Session = Depends(get_db),
    _: User = Depends(require_board),
):
    proposals = board_service.list_proposals(db, node_id, proposal_status)
    return [BoardProposalOut.from_model(p, include_transcript) for p in proposals]


@app.get("/proposals/{proposal_id}", response_model=BoardProposalOut)
def get_proposal(
    proposal_id: int, include_transcript: bool = False, db: Session = Depends(get_db), _: User = Depends(require_board)
):
    proposal = board_service.get_proposal_or_404(db, proposal_id)
    return BoardProposalOut.from_model(proposal, include_transcript)


@app.post("/proposals/{proposal_id}/respond", response_model=ApplyResultOut)
def respond_to_proposal(
    proposal_id: int,
    payload: ProposalDecisionRequest,
    include_transcript: bool = False,
    db: Session = Depends(get_db),
    user: User = Depends(require_board),
):
    """Stage 2/3/4-6: the employee's decision on the council's latest
    conclusion. "reject" needs a comment and loops back to stage 1 with it as
    context (a new round on the same proposal). "accept" edits the node and
    cascades the change down through its descendants and up through its
    ancestors."""
    proposal = board_service.get_proposal_or_404(db, proposal_id)
    if payload.decision == "reject":
        proposal = board_council.add_round(db, proposal, payload.comment or "")
        return ApplyResultOut(proposal=BoardProposalOut.from_model(proposal, include_transcript), changes=[])

    proposal, changes = board_council.apply_proposal(db, proposal, user)
    return ApplyResultOut(
        proposal=BoardProposalOut.from_model(proposal, include_transcript),
        changes=[BoardNodeChangeOut.model_validate(c) for c in changes],
    )


@app.delete("/proposals/{proposal_id}", response_model=BoardProposalOut)
def cancel_proposal(proposal_id: int, db: Session = Depends(get_db), _: User = Depends(require_board)):
    """Discards a pending proposal without looping back - for when the
    employee just wants to drop it instead of rejecting-with-a-comment."""
    proposal = board_service.get_proposal_or_404(db, proposal_id)
    proposal = board_council.cancel_proposal(db, proposal)
    return BoardProposalOut.from_model(proposal, include_transcript=False)


@app.post("/actualize", response_model=ActualizeResultOut)
def actualize(db: Session = Depends(get_db), user: User = Depends(require_admin)):
    """Refreshes the whole tree's descriptions/statuses from real, current
    operational data (tasks, clients, production, warehouse, ...) - no
    council, no proposal, applied directly. Admin-only: this is a system-wide
    pass over the whole company tree, not a per-node discussion."""
    root = board_service.get_root(db)
    if root is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Дерево ещё не создано")
    changes = board_actualize.actualize(db, root, user)
    return ActualizeResultOut(generated_at=datetime.now(timezone.utc), changes=[BoardNodeChangeOut.model_validate(c) for c in changes])
