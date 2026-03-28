from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class DocumentCreate(BaseModel):
    title: str
    document_type_id: int
    number: Optional[str] = None
    year: Optional[int] = None
    document_date: Optional[date] = None
    sector_id: int
    author_origin: Optional[str] = None
    subject: Optional[str] = None
    keywords: Optional[str] = None
    access_level: str = "interno"
    status: str = "ativo"
    notes: Optional[str] = None


class DocumentOut(BaseModel):
    id: int
    title: str
    document_type_id: int
    number: Optional[str] = None
    year: Optional[int] = None
    document_date: Optional[date] = None
    sector_id: int
    author_origin: Optional[str] = None
    subject: Optional[str] = None
    keywords: Optional[str] = None
    access_level: str
    status: str
    notes: Optional[str] = None
    original_file_path: str
    ocr_file_path: Optional[str] = None
    extracted_text: Optional[str] = None
    ocr_status: str
    created_by: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)