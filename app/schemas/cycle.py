from pydantic import BaseModel, ConfigDict

from app.models.enums import CycleStatus
from app.schemas.client import ClientOut
from app.schemas.installation import InstallationOut
from app.schemas.production import ProductionOut


class CycleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: CycleStatus
    client: ClientOut | None
    production: ProductionOut | None
    installation: InstallationOut | None
