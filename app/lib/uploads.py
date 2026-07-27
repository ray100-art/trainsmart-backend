"""Shared upload size limits for CSV imports."""
from fastapi import HTTPException, UploadFile, status

# 2 MB — enough for thousands of CSV rows; blocks memory DoS
MAX_UPLOAD_BYTES = 2 * 1024 * 1024


def read_upload_text(file: UploadFile, max_bytes: int = MAX_UPLOAD_BYTES) -> str:
    """Read an uploaded file with a hard size cap, decode as text."""
    raw = file.file.read(max_bytes + 1)
    if len(raw) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum upload size is {max_bytes // (1024 * 1024)} MB.",
        )
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        return raw.decode("latin-1")
