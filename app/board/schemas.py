from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.board.models import BoardChangeSource, BoardChangeType, BoardNodeColor, BoardProposalStatus


class BoardNodeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    parent_id: int | None
    level: int
    sort_order: int
    title: str
    description: str
    color: BoardNodeColor
    created_at: datetime
    updated_at: datetime
    children: list["BoardNodeOut"] = []

    @staticmethod
    def from_model(node) -> "BoardNodeOut":
        return BoardNodeOut(
            id=node.id,
            parent_id=node.parent_id,
            level=node.level,
            sort_order=node.sort_order,
            title=node.title,
            description=node.description,
            color=node.color,
            created_at=node.created_at,
            updated_at=node.updated_at,
            children=[BoardNodeOut.from_model(c) for c in node.children],
        )


BoardNodeOut.model_rebuild()


class BoardNodeBriefOut(BaseModel):
    id: int
    title: str
    level: int
    color: BoardNodeColor


class BoardNodeDetailOut(BoardNodeOut):
    path: list[BoardNodeBriefOut] = []  # ancestors from root to this node, root first

    @staticmethod
    def from_model_with_path(node, path: list) -> "BoardNodeDetailOut":
        return BoardNodeDetailOut(
            id=node.id,
            parent_id=node.parent_id,
            level=node.level,
            sort_order=node.sort_order,
            title=node.title,
            description=node.description,
            color=node.color,
            created_at=node.created_at,
            updated_at=node.updated_at,
            children=[BoardNodeOut.from_model(c) for c in node.children],
            path=[BoardNodeBriefOut(id=a.id, title=a.title, level=a.level, color=a.color) for a in path],
        )


class BoardNodeUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=255)
    description: str | None = None
    color: BoardNodeColor | None = None


class ProposeChangeRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


class ProposalDecisionRequest(BaseModel):
    decision: Literal["accept", "reject"]
    comment: str | None = Field(default=None, max_length=4000)


class CouncilOpinionOut(BaseModel):
    role: str
    role_label: str
    opinion: str
    stance: str


class ProposalRoundOut(BaseModel):
    user_message: str
    summary: str
    recommendation: Literal["change", "no_change"]
    proposed_title: str | None
    proposed_description: str | None
    proposed_color: BoardNodeColor | None
    decision: Literal["pending", "accepted", "rejected"]
    council: list[CouncilOpinionOut] = []
    production_snapshot: dict | None = None
    research_brief: str | None = None


class BoardProposalOut(BaseModel):
    id: int
    node_id: int
    requested_by_id: int
    status: BoardProposalStatus
    created_at: datetime
    applied_at: datetime | None
    rounds: list[ProposalRoundOut]

    @staticmethod
    def from_model(proposal, include_transcript: bool) -> "BoardProposalOut":
        rounds = []
        for r in proposal.rounds:
            council = [CouncilOpinionOut(**c) for c in r.get("council", [])] if include_transcript else []
            rounds.append(
                ProposalRoundOut(
                    user_message=r.get("user_message", ""),
                    summary=r.get("summary", ""),
                    recommendation=r.get("recommendation", "no_change"),
                    proposed_title=r.get("proposed_title"),
                    proposed_description=r.get("proposed_description"),
                    proposed_color=r.get("proposed_color"),
                    decision=r.get("decision", "pending"),
                    council=council,
                    production_snapshot=r.get("production_snapshot"),
                    research_brief=r.get("research_brief"),
                )
            )
        return BoardProposalOut(
            id=proposal.id,
            node_id=proposal.node_id,
            requested_by_id=proposal.requested_by_id,
            status=proposal.status,
            created_at=proposal.created_at,
            applied_at=proposal.applied_at,
            rounds=rounds,
        )


class BoardNodeChangeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    node_id: int
    proposal_id: int | None
    source: BoardChangeSource
    change_type: BoardChangeType
    title: str
    old_description: str | None
    new_description: str | None
    old_color: str | None
    new_color: str | None
    note: str | None
    created_at: datetime


class ApplyResultOut(BaseModel):
    proposal: BoardProposalOut
    changes: list[BoardNodeChangeOut]


class ActualizeResultOut(BaseModel):
    generated_at: datetime
    changes: list[BoardNodeChangeOut]
