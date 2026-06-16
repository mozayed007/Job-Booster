"""Shared upload validation helpers."""

from pathlib import Path

from fastapi import HTTPException, UploadFile

MAX_UPLOAD_BYTES = 10 * 1024 * 1024

RESUME_EXTENSIONS = {".pdf", ".docx", ".md", ".txt", ".tex"}
SPREADSHEET_EXTENSIONS = {".csv", ".xlsx", ".xls"}


def validate_upload(
    file: UploadFile,
    *,
    max_bytes: int = MAX_UPLOAD_BYTES,
    allowed_extensions: set[str] | None = None,
    allowed_content_types: set[str] | None = None,
) -> None:
    """Validate filename extension and content type before reading bytes."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    ext = Path(file.filename).suffix.lower()
    if allowed_extensions and ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file extension: {ext}",
        )
    if allowed_content_types and file.content_type not in allowed_content_types:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported content type: {file.content_type}",
        )


def validate_upload_size(content: bytes, *, max_bytes: int = MAX_UPLOAD_BYTES) -> None:
    """Validate uploaded bytes do not exceed the configured maximum."""
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds maximum size of {max_bytes} bytes",
        )
