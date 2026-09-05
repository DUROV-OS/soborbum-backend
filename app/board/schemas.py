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
    # 2-3 paragraph AI condensation of `description` (500+ words - see
    # app.board.prompts._SCOPE_DISCIPLINE) - what the frontend should display
    # instead of the full text. None only for a node whose description
    # predates this field and hasn't been touched by an AI edit since.
    summary: str | None
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
            summary=node.summary,
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
            summary=node.summary,
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


class CreateDiscussionRequest(BaseModel):
    node_id: int | None = None  # None -> обсуждение по компании в целом
    title: str | None = Field(default=None, max_length=255)
    message: str | None = Field(default=None, max_length=8000)  # необязательная первая реплика


class PostDiscussionMessageRequest(BaseModel):
    message: str = Field(min_length=1, max_length=8000)
    # true -> перед ответом опросить 7 ролей совета (только если обсуждение привязано к ноде)
    consult_council: bool = False


class RenameDiscussionRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)


class BoardDiscussionMessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    role: Literal["user", "assistant"]
    author_id: int | None
    content: str
    council: list[CouncilOpinionOut] | None = None
    research_brief: str | None = None
    created_at: datetime


class BoardDiscussionOut(BaseModel):
    id: int
    node_id: int | None
    created_by_id: int
    title: str
    created_at: datetime
    updated_at: datetime
    message_count: int

    @staticmethod
    def from_model(discussion) -> "BoardDiscussionOut":
        return BoardDiscussionOut(
            id=discussion.id,
            node_id=discussion.node_id,
            created_by_id=discussion.created_by_id,
            title=discussion.title,
            created_at=discussion.created_at,
            updated_at=discussion.updated_at,
            message_count=len(discussion.messages),
        )


class BoardDiscussionDetailOut(BoardDiscussionOut):
    messages: list[BoardDiscussionMessageOut] = []

    @staticmethod
    def from_model(discussion) -> "BoardDiscussionDetailOut":
        return BoardDiscussionDetailOut(
            id=discussion.id,
            node_id=discussion.node_id,
            created_by_id=discussion.created_by_id,
            title=discussion.title,
            created_at=discussion.created_at,
            updated_at=discussion.updated_at,
            message_count=len(discussion.messages),
            messages=[BoardDiscussionMessageOut.model_validate(m) for m in discussion.messages],
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
