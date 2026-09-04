"""The Claude tool-use loop: sends a chat's history to the model, executes
(or gates behind approval) whatever tools it calls, and keeps going until
the model produces a final text answer or the turn pauses on PendingAction.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone

import anthropic
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.ai.models import Chat, ChatMode, Message, PendingAction, PendingActionStatus
from app.ai.prompts import SYSTEM_PROMPTS
from app.ai.tools import DOMAIN_TOOLS, TOOLS
from app.core.config import settings
from app.users.models import User

MAX_ITERATIONS = 8
MCP_BETA = "mcp-client-2025-04-04"


@dataclass
class TurnResult:
    status: str  # "completed" | "pending_approval"
    reply: str | None = None
    pending_actions: list[PendingAction] = field(default_factory=list)


def _get_client() -> anthropic.Anthropic:
    if not settings.anthropic_api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ИИ не настроен: не задан ANTHROPIC_API_KEY (см. backend/.env)",
        )
    return anthropic.Anthropic(api_key=settings.anthropic_api_key)


def _available_tools(chat: Chat, user: User) -> list[dict]:
    tools = []
    for name in DOMAIN_TOOLS[chat.domain]:
        tool_def = TOOLS[name]
        if not user.has_access(tool_def.required_module):
            continue
        if chat.mode == ChatMode.NO_ACTIONS and not tool_def.read_only:
            continue
        tools.append(tool_def.schema)
    return tools


def _build_history(chat: Chat) -> list[dict]:
    return [{"role": m.role, "content": m.content} for m in chat.messages]


def _call_claude(system: str, messages: list[dict], tools: list[dict]):
    client = _get_client()
    kwargs = {
        "model": settings.ai_model,
        "max_tokens": 2048,
        "system": system,
        "messages": messages,
    }
    if tools:
        kwargs["tools"] = tools

    if settings.mcp_server_url:
        return client.beta.messages.create(
            betas=[MCP_BETA],
            mcp_servers=[
                {
                    "type": "url",
                    "url": settings.mcp_server_url,
                    "name": "knowledge-base",
                    "authorization_token": settings.mcp_server_token,
                }
            ],
            **kwargs,
        )
    return client.messages.create(**kwargs)


def _to_tool_result(tool_use_id: str, resolution: dict) -> dict:
    content = resolution.get("content")
    text = content if isinstance(content, str) else json.dumps(content, ensure_ascii=False, default=str)
    return {
        "type": "tool_result",
        "tool_use_id": tool_use_id,
        "content": text,
        "is_error": bool(resolution.get("is_error", False)),
    }


def _execute_tool(db: Session, name: str, tool_input: dict, user: User) -> dict:
    tool_def = TOOLS.get(name)
    if tool_def is None:
        return {"content": {"error": f"Неизвестный инструмент: {name}"}, "is_error": True}
    try:
        result = tool_def.handler(db, user, **tool_input)
        db.commit()
        return {"content": result, "is_error": False}
    except HTTPException as e:
        db.rollback()
        return {"content": {"error": e.detail}, "is_error": True}


def run_turn(db: Session, chat: Chat, user: User, user_text: str) -> TurnResult:
    db.add(Message(chat_id=chat.id, role="user", content=[{"type": "text", "text": user_text}]))
    db.commit()
    db.refresh(chat)
    return _advance(db, chat, user)


def _advance(db: Session, chat: Chat, user: User) -> TurnResult:
    for _ in range(MAX_ITERATIONS):
        system = SYSTEM_PROMPTS[chat.domain]
        history = _build_history(chat)
        tools = _available_tools(chat, user)
        response = _call_claude(system, history, tools)

        content_blocks = [block.model_dump(mode="json") for block in response.content]
        assistant_message = Message(chat_id=chat.id, role="assistant", content=content_blocks)
        db.add(assistant_message)
        db.commit()
        db.refresh(assistant_message)

        if response.stop_reason != "tool_use":
            text = "".join(b.get("text", "") for b in content_blocks if b.get("type") == "text")
            return TurnResult(status="completed", reply=text)

        tool_use_blocks = [b for b in content_blocks if b.get("type") == "tool_use"]
        resolutions: dict[str, dict] = {}
        pending: list[PendingAction] = []

        for block in tool_use_blocks:
            tool_use_id, name, tool_input = block["id"], block["name"], block.get("input", {})
            tool_def = TOOLS.get(name)

            if tool_def is not None and not tool_def.read_only and chat.mode == ChatMode.REQUIRE_APPROVAL:
                pa = PendingAction(
                    chat_id=chat.id,
                    message_id=assistant_message.id,
                    tool_use_id=tool_use_id,
                    tool_name=name,
                    tool_input=tool_input,
                )
                db.add(pa)
                db.commit()
                db.refresh(pa)
                pending.append(pa)
                resolutions[tool_use_id] = {"status": "pending"}
            else:
                outcome = _execute_tool(db, name, tool_input, user)
                resolutions[tool_use_id] = {"status": "executed", **outcome}

        assistant_message.tool_resolutions = resolutions
        db.add(assistant_message)
        db.commit()

        if pending:
            return TurnResult(status="pending_approval", pending_actions=pending)

        tool_result_content = [_to_tool_result(tid, res) for tid, res in resolutions.items()]
        db.add(Message(chat_id=chat.id, role="user", content=tool_result_content))
        db.commit()
        db.refresh(chat)

    return TurnResult(
        status="completed",
        reply="Достигнут лимит шагов обработки запроса. Попробуй сформулировать вопрос иначе.",
    )


def resolve_pending_action(db: Session, pending_action: PendingAction, approve: bool, decided_by: User) -> TurnResult:
    if pending_action.status != PendingActionStatus.PENDING:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Это действие уже обработано")

    pending_action.status = PendingActionStatus.APPROVED if approve else PendingActionStatus.REJECTED
    pending_action.decided_by_id = decided_by.id
    pending_action.decided_at = datetime.now(timezone.utc)
    db.add(pending_action)
    db.commit()

    if approve:
        outcome = _execute_tool(db, pending_action.tool_name, pending_action.tool_input, decided_by)
        resolution = {"status": "executed", **outcome}
    else:
        resolution = {"status": "executed", "content": {"error": "Действие отклонено сотрудником"}, "is_error": True}

    message = pending_action.message
    resolutions = dict(message.tool_resolutions or {})
    resolutions[pending_action.tool_use_id] = resolution
    message.tool_resolutions = resolutions
    db.add(message)
    db.commit()
    db.refresh(message)

    tool_use_ids = [b["id"] for b in message.content if b.get("type") == "tool_use"]
    still_pending = (
        db.query(PendingAction)
        .filter(PendingAction.message_id == message.id, PendingAction.status == PendingActionStatus.PENDING)
        .all()
    )
    if still_pending:
        return TurnResult(status="pending_approval", pending_actions=still_pending)

    tool_result_content = [_to_tool_result(tid, resolutions[tid]) for tid in tool_use_ids]
    chat = pending_action.chat
    db.add(Message(chat_id=chat.id, role="user", content=tool_result_content))
    db.commit()
    db.refresh(chat)

    return _advance(db, chat, decided_by)
