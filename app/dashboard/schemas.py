from datetime import datetime
from typing import Literal

from pydantic import BaseModel

WidgetTone = Literal["neutral", "brand", "success", "warning", "danger", "info"]


class DashboardWidget(BaseModel):
    section: str
    title: str
    value: str
    hint: str | None = None
    tone: WidgetTone = "neutral"


class TodayDashboardOut(BaseModel):
    generated_at: datetime
    summary: str
    widgets: list[DashboardWidget]
