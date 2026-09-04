"""Files attached to AI chat messages. An employee uploads a file and gets a
FileAsset id back; the chat message then stores a lightweight {"type":
"file_ref", ...} block referencing it, instead of the base64 payload Claude
actually needs - that keeps chat history cheap to store and list. The real
content block is built on demand, right before a turn is sent to Claude, from
the file on disk - see engine._resolve_content.
"""

import base64

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.common.files import FileAsset, FilePurpose, save_upload_file
from app.users.models import User

# Anthropic caps a single request at ~32MB; leave headroom for conversation
# history (every attachment gets resent as base64 on every turn) and for more
# than one file per message.
MAX_ATTACHMENT_BYTES = 20 * 1024 * 1024

IMAGE_MEDIA_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
PDF_MEDIA_TYPE = "application/pdf"
TEXT_MEDIA_TYPES = {"text/plain", "text/csv", "text/markdown", "application/json"}
ALLOWED_MEDIA_TYPES = IMAGE_MEDIA_TYPES | TEXT_MEDIA_TYPES | {PDF_MEDIA_TYPE}


def upload_attachment(db: Session, upload_file: UploadFile, user: User) -> FileAsset:
    content_type = upload_file.content_type or "application/octet-stream"
    if content_type not in ALLOWED_MEDIA_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Неподдерживаемый тип файла для ИИ-чата: {content_type}",
        )

    upload_file.file.seek(0, 2)
    size = upload_file.file.tell()
    upload_file.file.seek(0)
    if size > MAX_ATTACHMENT_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Файл слишком большой для ИИ-чата (максимум 20 МБ)",
        )

    return save_upload_file(db, upload_file, FilePurpose.AI_CHAT_ATTACHMENT, user)


def resolve_file_ids(db: Session, file_ids: list[int], user: User) -> list[dict]:
    """Turn user-supplied file ids into file_ref blocks, checking the caller
    actually uploaded each one themselves."""
    blocks = []
    for file_id in file_ids:
        asset = db.get(FileAsset, file_id)
        if (
            asset is None
            or asset.purpose != FilePurpose.AI_CHAT_ATTACHMENT
            or asset.uploaded_by_id != user.id
        ):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Файл {file_id} не найден")
        blocks.append(
            {"type": "file_ref", "file_id": asset.id, "filename": asset.filename, "content_type": asset.content_type}
        )
    return blocks


def build_content_block(asset: FileAsset) -> dict:
    try:
        with open(asset.path_on_disk, "rb") as f:
            raw = f.read()
    except OSError:
        return {"type": "text", "text": f"[Файл «{asset.filename}» больше недоступен]"}

    if asset.content_type in IMAGE_MEDIA_TYPES:
        return {
            "type": "image",
            "source": {"type": "base64", "media_type": asset.content_type, "data": base64.b64encode(raw).decode()},
        }
    if asset.content_type == PDF_MEDIA_TYPE:
        return {
            "type": "document",
            "source": {"type": "base64", "media_type": PDF_MEDIA_TYPE, "data": base64.b64encode(raw).decode()},
            "title": asset.filename,
        }
    return {
        "type": "document",
        "source": {"type": "text", "media_type": "text/plain", "data": raw.decode("utf-8", errors="replace")},
        "title": asset.filename,
    }
