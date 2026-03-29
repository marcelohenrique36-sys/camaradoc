import os
import shutil
from uuid import uuid4
from fastapi import UploadFile
from app.core.config import settings


def ensure_directories():
    os.makedirs(settings.STORAGE_ORIGINAL, exist_ok=True)
    os.makedirs(settings.STORAGE_OCR, exist_ok=True)
    os.makedirs(settings.STORAGE_TEMP, exist_ok=True)


def save_uploaded_pdf(upload: UploadFile) -> str:
    ext = os.path.splitext(upload.filename)[1].lower()
    if ext != ".pdf":
        raise ValueError("Somente arquivos PDF sao permitidos")

    filename = f"{uuid4().hex}.pdf"
    destination = os.path.join(settings.STORAGE_ORIGINAL, filename)

    with open(destination, "wb") as buffer:
        shutil.copyfileobj(upload.file, buffer)

    return destination


def resolve_storage_path(path: str) -> str | None:
    if not path:
        return None

    path_abs = os.path.abspath(path)
    allowed_roots = [
        os.path.abspath(settings.STORAGE_ORIGINAL),
        os.path.abspath(settings.STORAGE_OCR),
        os.path.abspath(settings.STORAGE_TEMP),
    ]

    for root in allowed_roots:
        try:
            common = os.path.commonpath([path_abs, root])
        except ValueError:
            continue

        if common == root:
            return path_abs

    return None
