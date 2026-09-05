from pydantic import BaseModel, ConfigDict

from app.clients.schemas import ClientOut
from app.cycle.models import CycleStatus
from app.installation.schemas import InstallationOut
from app.production.schemas import ProductionOut


class CycleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: CycleStatus
    client: ClientOut | None
    # productions holds one project per дом (множественный заказ); `production`
    # stays for backwards compatibility and points at the first дом.
    productions: list[ProductionOut] = []
    production: ProductionOut | None
    installation: InstallationOut | None
