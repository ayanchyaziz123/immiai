import logging

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from ....services.document_service import (
    MAX_FILE_BYTES,
    MAX_TEXT_CHARS,
    SUPPORTED_EXTENSIONS,
    extract_text,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/upload", tags=["upload"])


class UploadResponse(BaseModel):
    text: str
    filename: str
    chars: int
    pages: int | None = None
    method: str
    truncated: bool


@router.post("/", response_model=UploadResponse)
async def upload_document(file: UploadFile = File(...)):
    content = await file.read()

    if len(content) > MAX_FILE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {MAX_FILE_BYTES // 1024 // 1024} MB.",
        )

    if not content:
        raise HTTPException(status_code=422, detail="Uploaded file is empty.")

    try:
        text, method = extract_text(content, file.filename or "", file.content_type or "")
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"Document extraction failed for {file.filename}: {e}")
        raise HTTPException(status_code=500, detail=f"Could not read file: {e}")

    truncated = len(text) > MAX_TEXT_CHARS
    trimmed   = text[:MAX_TEXT_CHARS] if truncated else text

    return UploadResponse(
        text      = trimmed,
        filename  = file.filename or "document",
        chars     = len(text),
        method    = method,
        truncated = truncated,
    )


@router.get("/supported-types")
def supported_types():
    return {"extensions": sorted(SUPPORTED_EXTENSIONS)}
