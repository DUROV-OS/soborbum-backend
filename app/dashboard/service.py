"""Builds the "Сегодня" dashboard: pulls real aggregated numbers out of every
section the current user has access to, then asks Claude to pick 1-2 widgets
per section and write them up. The model never invents numbers - it only
sees the JSON snapshot built here and is forced (tool_choice) to reply by
calling submit_dashboard with values drawn from that snapshot.
"""

import json
from datetime import date, datetime, timedelta, timezone
from typing import Callable

import anthropic
from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.ai import cache as ai_cache
from app.clients.models import Client, ClientStage
from app.common.module_access import Module
from app.core.config import settings
from app.cycle.models import Cycle, CycleStatus
from app.dashboard.schemas import DashboardWidget, TodayDashboardOut
from app.installation.models import Installation, InstallationStage
from app.marketing.models import ContentItem, ContentStage
from app.production.models import MaterialRequest, MaterialRequestStatus, ModuleMaterial, ProductionModule
from app.tasks.models import Task, TaskStatus
from app.users.models import User, UserRole
from app.warehouse import service as warehouse_service
from app.warehouse.models import Supply

VALID_TONES = {"neutral", "brand", "success", "warning", "danger", "info"}
MAX_WIDGETS_PER_SECTION = 2

SECTION_LABELS: dict[str, str] = {
    "clients": "Клиенты",
    "production": "Производство",
    "installation": "Монтаж",
    "cycle": "Цикл клиента",
    "warehouse": "Склад",
    "marketing": "Маркетинг",
    "tasks": "Задачи",
    "users": "Сотрудники",
}


# ------------------------------------------------------------- snapshots --

def _snapshot_clients(db: Session) -> dict:
    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)
    two_weeks_ago = now - timedelta(days=14)

    stage_counts = dict.fromkeys([s.value for s in ClientStage], 0)
    for stage, count in db.query(Client.stage, func.count(Client.id)).group_by(Client.stage).all():
        stage_counts[stage.value] = count

    return {
        "total_clients": sum(stage_counts.values()),
        "stage_counts": stage_counts,
        "awaiting_payment_confirmation": db.query(Client)
        .filter(Client.stage == ClientStage.PAYMENT, Client.is_paid.isnot(True))
        .count(),
        "new_leads_last_7_days": db.query(Client)
        .filter(Client.stage == ClientStage.LEAD, Client.created_at >= week_ago)
        .count(),
        "leads_stuck_over_14_days": db.query(Client)
        .filter(Client.stage == ClientStage.LEAD, Client.created_at < two_weeks_ago)
        .count(),
    }


def _snapshot_cycle(db: Session) -> dict:
    status_counts = dict.fromkeys([s.value for s in CycleStatus], 0)
    for cycle_status, count in db.query(Cycle.status, func.count(Cycle.id)).group_by(Cycle.status).all():
        status_counts[cycle_status.value] = count
    return {"total_cycles": sum(status_counts.values()), "status_counts": status_counts}


def _snapshot_installation(db: Session) -> dict:
    today = date.today()
    week_ahead = today + timedelta(days=7)

    stage_counts = dict.fromkeys([s.value for s in InstallationStage], 0)
    for stage, count in db.query(Installation.stage, func.count(Installation.id)).group_by(Installation.stage).all():
        stage_counts[stage.value] = count

    return {
        "total_installations": sum(stage_counts.values()),
        "stage_counts": stage_counts,
        "scheduled_next_7_days": db.query(Installation)
        .filter(
            Installation.scheduled_date.isnot(None),
            Installation.scheduled_date >= today,
            Installation.scheduled_date <= week_ahead,
        )
        .count(),
        "overdue_not_completed": db.query(Installation)
        .filter(
            Installation.scheduled_date.isnot(None),
            Installation.scheduled_date < today,
            Installation.stage != InstallationStage.FOLLOWUP,
        )
        .count(),
        "unscheduled": db.query(Installation).filter(Installation.scheduled_date.is_(None)).count(),
    }


def _snapshot_marketing(db: Session) -> dict:
    today = date.today()
    week_ahead = today + timedelta(days=7)
    not_released = [ContentStage.IDEA, ContentStage.GATHERING, ContentStage.EDITING]

    stage_counts = dict.fromkeys([s.value for s in ContentStage], 0)
    for stage, count in db.query(ContentItem.stage, func.count(ContentItem.id)).group_by(ContentItem.stage).all():
        stage_counts[stage.value] = count

    return {
        "total_content_items": sum(stage_counts.values()),
        "stage_counts": stage_counts,
        "release_due_next_7_days": db.query(ContentItem)
        .filter(
            ContentItem.stage.in_(not_released),
            ContentItem.planned_release_date.isnot(None),
            ContentItem.planned_release_date >= today,
            ContentItem.planned_release_date <= week_ahead,
        )
        .count(),
        "release_overdue": db.query(ContentItem)
        .filter(
            ContentItem.stage.in_(not_released),
            ContentItem.planned_release_date.isnot(None),
            ContentItem.planned_release_date < today,
        )
        .count(),
    }


def _snapshot_production(db: Session) -> dict:
    shortfall_module_ids = {
        row[0]
        for row in db.query(ModuleMaterial.module_id)
        .filter(ModuleMaterial.quantity_provided < ModuleMaterial.quantity_required)
        .distinct()
        .all()
    }
    return {
        "total_modules": db.query(ProductionModule).count(),
        "modules_with_material_shortfall": len(shortfall_module_ids),
        "pending_material_requests": db.query(MaterialRequest)
        .filter(MaterialRequest.status == MaterialRequestStatus.PENDING)
        .count(),
    }


def _snapshot_warehouse(db: Session) -> dict:
    materials = warehouse_service.list_materials(db)
    needs_supply = [m for m in materials if m.needs_supply]
    week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    top_shortage = sorted(needs_supply, key=lambda m: m.quantity_in_stock - m.threshold)[:5]
    return {
        "total_materials": len(materials),
        "materials_needing_supply": len(needs_supply),
        "supplies_recorded_last_7_days": db.query(Supply).filter(Supply.created_at >= week_ago).count(),
        "top_shortage_materials": [
            {
                "title": m.title,
                "warehouse": m.warehouse.value,
                "quantity_in_stock": m.quantity_in_stock,
                "threshold": m.threshold,
            }
            for m in top_shortage
        ],
    }


def _snapshot_tasks(db: Session) -> dict:
    now = datetime.now(timezone.utc)
    status_counts = dict.fromkeys([s.value for s in TaskStatus], 0)
    for task_status, count in db.query(Task.status, func.count(Task.id)).group_by(Task.status).all():
        status_counts[task_status.value] = count

    open_tasks = db.query(Task).filter(Task.status != TaskStatus.DONE).all()
    overdue = sum(1 for t in open_tasks if t.deadline and t.deadline < now)
    due_today = sum(1 for t in open_tasks if t.deadline and t.deadline.date() == now.date())

    return {
        "total_tasks": sum(status_counts.values()),
        "status_counts": status_counts,
        "open_tasks": len(open_tasks),
        "overdue_tasks": overdue,
        "due_today": due_today,
    }


def _snapshot_users(db: Session) -> dict:
    active_users = db.query(User).filter(User.is_active.is_(True)).all()
    workers = [u for u in active_users if u.role == UserRole.WORKER]

    workload = []
    for u in workers:
        open_count = (
            db.query(Task)
            .filter(Task.assignees.any(User.id == u.id), Task.status != TaskStatus.DONE)
            .count()
        )
        workload.append({"full_name": u.full_name, "open_tasks": open_count})
    workload.sort(key=lambda w: w["open_tasks"], reverse=True)

    return {
        "active_employees": len(active_users),
        "workers_without_module_access": sum(1 for u in workers if not u.module_access),
        "top_workload": workload[:5],
    }


SECTION_BUILDERS: dict[str, tuple[Module, Callable[[Session], dict]]] = {
    "clients": (Module.CLIENTS, _snapshot_clients),
    "production": (Module.PRODUCTION, _snapshot_production),
    "installation": (Module.INSTALLATION, _snapshot_installation),
    "cycle": (Module.CYCLE, _snapshot_cycle),
    "warehouse": (Module.WAREHOUSE, _snapshot_warehouse),
    "marketing": (Module.MARKETING, _snapshot_marketing),
    "tasks": (Module.TASKS, _snapshot_tasks),
}


def build_snapshot(db: Session, user: User) -> dict[str, dict]:
    snapshot = {key: builder(db) for key, (module, builder) in SECTION_BUILDERS.items() if user.has_access(module)}
    if user.role == UserRole.ADMIN:
        snapshot["users"] = _snapshot_users(db)
    return snapshot


# ------------------------------------------------------------------ Claude --

SUBMIT_TOOL_NAME = "submit_dashboard"

SYSTEM_PROMPT = (
    "Ты — аналитик системы управления производством модульных домов «Soborbum». Тебе передан JSON "
    "с реальными агрегированными цифрами по разделам предприятия на текущий момент — только по тем "
    "разделам, к которым у сотрудника есть доступ. Собери из них сводку «Сегодня».\n\n"
    "Правила:\n"
    "- Для каждого раздела, который есть в переданных данных, выбери 1-2 самых важных сейчас "
    "показателя и оформи их виджетами. Не создавай виджеты для разделов, которых нет в данных.\n"
    "- Приоритет — тревожным и требующим внимания сегодня фактам (просрочки, дефицит, накопившиеся "
    "заявки, застрявшие клиенты), а не первому попавшемуся счётчику. Если в разделе всё спокойно, "
    "покажи это явно (например, «просрочек нет»), не выдумывая проблему.\n"
    "- value и hint должны быть основаны СТРОГО на переданных цифрах: можно форматировать, округлять, "
    "считать доли/проценты и суммы из переданных чисел, но нельзя вставлять числа, которых нет во "
    "входных данных.\n"
    "- tone: warning или danger — для тревожных значений (просрочки, дефицит, накопившиеся заявки), "
    "success — когда показатель хороший (например, просрочек нет), neutral/brand/info — для "
    "нейтральной информации.\n"
    "- title — короткий (2-4 слова), value — короткое число или фраза, hint — опциональное короткое "
    "пояснение.\n"
    "- summary — 1-2 предложения по-русски о самом важном на сегодня по всему предприятию в целом.\n"
    "- Отвечай ТОЛЬКО вызовом инструмента submit_dashboard, без текста."
)


def _build_tool_schema(sections: list[str]) -> dict:
    return {
        "name": SUBMIT_TOOL_NAME,
        "description": "Отправить готовую сводку «Сегодня»: краткое резюме и 1-2 виджета по каждому "
        "разделу, для которого переданы данные.",
        "input_schema": {
            "type": "object",
            "properties": {
                "summary": {
                    "type": "string",
                    "description": "1-2 предложения по-русски о самом важном на предприятии сегодня.",
                },
                "widgets": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "section": {"type": "string", "enum": sections},
                            "title": {"type": "string", "description": "Короткий заголовок виджета (2-4 слова)."},
                            "value": {"type": "string", "description": "Главное число/значение виджета."},
                            "hint": {"type": "string", "description": "Необязательное короткое пояснение."},
                            "tone": {"type": "string", "enum": sorted(VALID_TONES)},
                        },
                        "required": ["section", "title", "value", "tone"],
                    },
                },
            },
            "required": ["summary", "widgets"],
        },
    }


def _get_client() -> anthropic.Anthropic:
    if not settings.anthropic_api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ИИ не настроен: не задан ANTHROPIC_API_KEY (см. backend/.env)",
        )
    return anthropic.Anthropic(api_key=settings.anthropic_api_key)


def generate_widgets(db: Session, user: User, force: bool = False) -> TodayDashboardOut:
    cache_key = f"today_dashboard:{user.id}"
    cached = ai_cache.get(db, cache_key, force)
    if cached is not None:
        return TodayDashboardOut(**cached)

    snapshot = build_snapshot(db, user)
    if not snapshot:
        result = TodayDashboardOut(
            generated_at=datetime.now(timezone.utc),
            summary="Нет ни одного раздела с доступом для сводки.",
            widgets=[],
        )
        ai_cache.set(db, cache_key, result.model_dump(mode="json"), result.generated_at)
        return result

    client = _get_client()
    response = client.messages.create(
        model=settings.ai_model,
        max_tokens=1536,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": f"Данные на {date.today().isoformat()} по разделам, к которым есть доступ:\n\n"
                + json.dumps(snapshot, ensure_ascii=False, default=str),
            }
        ],
        tools=[_build_tool_schema(list(snapshot.keys()))],
        tool_choice={"type": "tool", "name": SUBMIT_TOOL_NAME},
    )

    tool_use = next((block for block in response.content if block.type == "tool_use"), None)
    if tool_use is None:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="ИИ не вернул сводку")

    payload = tool_use.input
    per_section_counts: dict[str, int] = {}
    widgets: list[DashboardWidget] = []
    for raw in payload.get("widgets", []):
        section = raw.get("section")
        if section not in snapshot or per_section_counts.get(section, 0) >= MAX_WIDGETS_PER_SECTION:
            continue
        per_section_counts[section] = per_section_counts.get(section, 0) + 1
        tone = raw.get("tone")
        widgets.append(
            DashboardWidget(
                section=section,
                title=raw.get("title", SECTION_LABELS.get(section, section)),
                value=str(raw.get("value", "")),
                hint=raw.get("hint"),
                tone=tone if tone in VALID_TONES else "neutral",
            )
        )

    result = TodayDashboardOut(
        generated_at=datetime.now(timezone.utc),
        summary=payload.get("summary", ""),
        widgets=widgets,
    )
    ai_cache.set(db, cache_key, result.model_dump(mode="json"), result.generated_at)
    return result
