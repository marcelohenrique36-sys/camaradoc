from datetime import datetime
from pydantic import BaseModel, EmailStr, ConfigDict


ROLE_ADMIN = "admin"
ROLE_PROTOCOLO = "protocolo_arquivo"
ROLE_CONSULTA_INTERNA = "consulta_interna"
ROLE_CONSULTA_PUBLICA = "consulta_publica"
VALID_ROLES = {
    ROLE_ADMIN,
    ROLE_PROTOCOLO,
    ROLE_CONSULTA_INTERNA,
    ROLE_CONSULTA_PUBLICA,
}


class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: str = ROLE_CONSULTA_INTERNA
    is_admin: bool = False


class UserRoleUpdate(BaseModel):
    role: str


class UserStatusUpdate(BaseModel):
    is_active: bool


class UserOut(BaseModel):
    id: int
    name: str
    email: EmailStr
    role: str
    is_admin: bool
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
