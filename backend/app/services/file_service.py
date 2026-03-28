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
        raise ValueError("Somente arquivos PDF são permitidos")

    filename = f"{uuid4().hex}.pdf"
    destination = os.path.join(settings.STORAGE_ORIGINAL, filename)

    with open(destination, "wb") as buffer:
        shutil.copyfileobj(upload.file, buffer)

    return destination