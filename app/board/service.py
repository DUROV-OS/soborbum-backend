from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.board.models import (
    BoardChangeSource,
    BoardChangeType,
    BoardNode,
    BoardNodeChange,
    BoardNodeColor,
    BoardProposal,
    BoardProposalStatus,
)
from app.users.models import User

# The root always has between 3 and 6 direct direction blocks (level 1); a
# direction's sub-directions (level 2) have no hard business rule, just a
# soft cap so a runaway AI structural edit can't blow up the tree.
DIRECTION_MIN = 3
DIRECTION_MAX = 6
SUBDIRECTION_SOFT_CAP = 12


def get_root(db: Session) -> BoardNode | None:
    return db.query(BoardNode).filter(BoardNode.parent_id.is_(None)).order_by(BoardNode.id).first()


def get_node_or_404(db: Session, node_id: int) -> BoardNode:
    node = db.get(BoardNode, node_id)
    if node is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Нода не найдена")
    return node


def get_proposal_or_404(db: Session, proposal_id: int) -> BoardProposal:
    proposal = db.get(BoardProposal, proposal_id)
    if proposal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Предложение не найдено")
    return proposal


def list_proposals(
    db: Session, node_id: int | None = None, proposal_status: BoardProposalStatus | None = None
) -> list[BoardProposal]:
    query = db.query(BoardProposal)
    if node_id is not None:
        query = query.filter(BoardProposal.node_id == node_id)
    if proposal_status is not None:
        query = query.filter(BoardProposal.status == proposal_status)
    return query.order_by(BoardProposal.id.desc()).all()


def node_path(node: BoardNode) -> list[BoardNode]:
    """Ancestors from root to (excluding) `node`."""
    path = []
    cur = node.parent
    while cur is not None:
        path.append(cur)
        cur = cur.parent
    path.reverse()
    return path


def flatten(node: BoardNode) -> list[BoardNode]:
    nodes = [node]
    for child in node.children:
        nodes.extend(flatten(child))
    return nodes


def safe_color(value: str | None) -> BoardNodeColor | None:
    if value in {c.value for c in BoardNodeColor}:
        return BoardNodeColor(value)
    return None


def log_change(
    db: Session,
    node: BoardNode,
    change_type: BoardChangeType,
    source: BoardChangeSource,
    proposal_id: int | None,
    actor: User | None,
    *,
    old_description: str | None = None,
    new_description: str | None = None,
    old_color: str | None = None,
    new_color: str | None = None,
    note: str | None = None,
) -> BoardNodeChange:
    change = BoardNodeChange(
        node_id=node.id,
        proposal_id=proposal_id,
        source=source,
        change_type=change_type,
        title=node.title,
        old_description=old_description,
        new_description=new_description,
        old_color=old_color,
        new_color=new_color,
        note=note,
        created_by_id=actor.id if actor else None,
    )
    db.add(change)
    return change


def update_node_manual(
    db: Session, node: BoardNode, title: str | None, description: str | None, color: BoardNodeColor | None, actor: User
) -> BoardNode:
    old_description, old_color = node.description, node.color.value
    changed = False
    if title is not None and title.strip() and title != node.title:
        node.title = title.strip()
        changed = True
    if description is not None and description != node.description:
        node.description = description
        changed = True
    if color is not None and color != node.color:
        node.color = color
        changed = True

    if changed:
        db.flush()
        log_change(
            db, node, BoardChangeType.UPDATED, BoardChangeSource.MANUAL, None, actor,
            old_description=old_description, new_description=node.description,
            old_color=old_color, new_color=node.color.value,
        )
    db.commit()
    db.refresh(node)
    return node


def apply_structural_ops(
    db: Session,
    parent: BoardNode,
    ops: dict,
    source: BoardChangeSource,
    proposal_id: int | None,
    actor: User | None,
    changes: list[BoardNodeChange],
) -> None:
    """Create/delete children of `parent`, per an AI-authored structural
    decision. Guarded by the direction-block count rule and a soft cap on
    sub-directions - see the module-level constants. Meant to be rare: every
    prompt that can populate `ops` is told this is for exceptional,
    company-wide changes only, not routine editing."""
    creates = list(ops.get("create") or [])
    delete_ids = {cid for cid in (ops.get("delete_child_ids") or []) if isinstance(cid, int)}
    note = ops.get("note")

    current = list(parent.children)
    current_ids = {c.id for c in current}
    deletable_ids = delete_ids & current_ids
    resulting_count = len(current) - len(deletable_ids) + len(creates)

    if parent.level == 0 and not (DIRECTION_MIN <= resulting_count <= DIRECTION_MAX):
        return  # would break the "3 to 6 direction blocks" rule - skip the whole op
    if parent.level == 1 and resulting_count > SUBDIRECTION_SOFT_CAP:
        keep = max(0, SUBDIRECTION_SOFT_CAP - (len(current) - len(deletable_ids)))
        creates = creates[:keep]

    for child_id in deletable_ids:
        child = next(c for c in current if c.id == child_id)
        changes.append(
            log_change(
                db, child, BoardChangeType.DELETED, source, proposal_id, actor,
                old_description=child.description, old_color=child.color.value, note=note,
            )
        )
        db.delete(child)
    db.flush()

    max_sort = max([c.sort_order for c in parent.children] + [-1])
    for i, spec in enumerate(creates):
        if not isinstance(spec, dict) or not spec.get("title"):
            continue
        new_node = BoardNode(
            parent_id=parent.id,
            level=parent.level + 1,
            sort_order=max_sort + 1 + i,
            title=str(spec["title"]).strip()[:255],
            description=str(spec.get("description") or ""),
            color=safe_color(spec.get("color")) or BoardNodeColor.GREEN,
        )
        db.add(new_node)
        db.flush()
        changes.append(
            log_change(
                db, new_node, BoardChangeType.CREATED, source, proposal_id, actor,
                new_description=new_node.description, new_color=new_node.color.value, note=note,
            )
        )
