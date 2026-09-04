"""Registry that lets domain services (clients, marketing, ...) react when a
linked task is marked DONE through the generic Tasks API, without task_service
having to import those domain services directly (avoids import cycles).

Closing a task in the *other* direction (a domain stage transition auto-closing
its transition task and creating the next one) is handled inline by the domain
services themselves via `close_open_link_tasks` / `create_link_task` below,
since that direction never needs to call back into task_service's status
machine — it force-closes directly.
"""

from typing import Callable

from sqlalchemy.orm import Session

from app.models.enums import TaskLinkType
from app.models.task import Task

_handlers: dict[TaskLinkType, Callable[[Session, Task], None]] = {}


def register(link_type: TaskLinkType):
    def decorator(fn: Callable[[Session, Task], None]):
        _handlers[link_type] = fn
        return fn

    return decorator


def handle_task_closed(db: Session, task: Task) -> None:
    handler = _handlers.get(task.link_type)
    if handler:
        handler(db, task)
