from typing import Optional
from pydantic import BaseModel, ConfigDict


class DocumentTypeCreate(BaseModel):
    name: str
    description: Optional[str] = None


class DocumentTypeUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class DocumentTypeOut(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    is_active: bool

    model_config = ConfigDict(from_attributes=True)
