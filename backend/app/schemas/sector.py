from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class SectorCreate(BaseModel):
    name: str
    description: Optional[str] = None


class SectorUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class SectorOut(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)