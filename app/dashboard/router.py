from fastapi import Depends, FastAPI
from sqlalchemy.orm import Session

from app.common.module_access import Module
from app.core.deps import require_module
from app.dashboard import service as dashboard_service
from app.dashboard.schemas import TodayDashboardOut
from app.db.session import get_db
from app.users.models import User

app = FastAPI(
    title="Soborbum — Сегодня",
    description="Сводка по всему предприятию на сегодня: ИИ собирает данные по каждому разделу, к "
    "которому у сотрудника есть доступ, и сам формирует 1-2 виджета с ключевыми показателями по "
    "каждому из них.",
    version="0.1.1",
)

require_ai = require_module(Module.AI)


@app.get("/today", response_model=TodayDashboardOut)
def get_today(db: Session = Depends(get_db), user: User = Depends(require_ai)):
    return dashboard_service.generate_widgets(db, user)
