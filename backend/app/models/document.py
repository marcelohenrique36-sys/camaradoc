from datetime import date, datetime
from typing import Optional
from sqlmodel import SQLModel, Field


class Document(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(index=True)
    document_type_id: int = Field(foreign_key="documenttype.id", index=True)
    number: Optional[str] = Field(default=None, index=True)
    year: Optional[int] = Field(default=None, index=True)
    document_date: Optional[date] = Field(default=None, index=True)
    sector_id: int = Field(foreign_key="sector.id", index=True)
    author_origin: Optional[str] = Field(default=None, index=True)
    subject: Optional[str] = None
    keywords: Optional[str] = None
    access_level: str = Field(default="interno", index=True)
    status: str = Field(default="ativo", index=True)
    notes: Optional[str] = None

    original_file_path: str
    ocr_file_path: Optional[str] = None
    extracted_text: Optional[str] = None
    ocr_status: str = Field(default="pending", index=True)
    ocr_error: Optional[str] = None

    created_by: int = Field(foreign_key="user.id", index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column_kwargs={"onupdate": datetime.utcnow},
    )
