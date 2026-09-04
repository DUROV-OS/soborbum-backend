import os
import uuid

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.enums import FilePurpose
from app.models.files import FileAsset
from app.models.user import User


def save_upload_file(db: Session, upload_file: UploadFile, purpose: FilePurpose, user: User) -> FileAsset:
    os.makedirs(settings.storage_dir, exist_ok=True)
    disk_name = f"{uuid.uuid4().hex}_{upload_file.filename}"
    path_on_disk = os.path.join(settings.storage_dir, disk_name)
    with open(path_on_disk, "wb") as f:
        f.write(upload_file.file.read())

    asset = FileAsset(
        filename=upload_file.filename or disk_name,
        content_type=upload_file.content_type or "application/octet-stream",
        path_on_disk=path_on_disk,
        purpose=purpose,
        uploaded_by_id=user.id,
    )
    db.add(asset)
    db.flush()
    return asset
