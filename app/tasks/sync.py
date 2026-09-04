"""Registry that lets domain sections (clients, marketing, warehouse, ...)
react when one of their linked tasks is marked DONE through the generic
Tasks API, without app.tasks.service importing those sections directly
(avoids import cycles, since those sections import app.tasks.service too).

The other sync direction - a domain stage transition auto-closing its
transition task and creating the next one - doesn't need this registry:
it's handled inline by the domain service via `close_open_link_task` /
`create_link_task` below, which force-close directly without calling back
into anything.
"""

from typing import Callable

from sqlalchemy.orm import Session

from app.tasks.models import Task, TaskLinkType

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
