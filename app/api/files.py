from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.enums import FilePurpose, Module
from app.models.files import FileAsset
from app.models.user import User

router = APIRouter(tags=["files"])

PURPOSE_MODULE = {
    FilePurpose.CONTRACT: Module.CLIENTS,
    FilePurpose.HOUSE_PROJECT: Module.CLIENTS,
    FilePurpose.TASK_IMAGE: Module.TASKS,
    FilePurpose.MARKETING_RAW: Module.MARKETING,
    FilePurpose.MARKETING_FINAL: Module.MARKETING,
}


@router.get("/files/{file_id}")
def download_file(file_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    asset = db.get(FileAsset, file_id)
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Файл не найден")
    required_module = PURPOSE_MODULE.get(asset.purpose)
    if required_module and not user.has_access(required_module):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Нет доступа к этому файлу")
    return FileResponse(asset.path_on_disk, media_type=asset.content_type, filename=asset.filename)
