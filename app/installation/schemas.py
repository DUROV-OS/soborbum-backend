from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from app.installation.models import InstallationStage


class InstallationUpdate(BaseModel):
    address: str | None = None
    scheduled_date: date | None = None
    notes: str | None = None


class InstallationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    cycle_id: int
    stage: InstallationStage
    address: str | None
    scheduled_date: date | None
    notes: str | None
    created_at: datetime
