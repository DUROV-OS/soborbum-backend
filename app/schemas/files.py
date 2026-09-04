from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import FilePurpose


class FileAssetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    content_type: str
    purpose: FilePurpose
    uploaded_by_id: int
    created_at: datetime
