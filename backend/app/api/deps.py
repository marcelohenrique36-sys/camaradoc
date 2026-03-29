from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session, select

from app.core.database import get_session
from app.core.security import decode_access_token
from app.models.user import User
from app.schemas.user import (
    ROLE_ADMIN,
    ROLE_CONSULTA_INTERNA,
    ROLE_CONSULTA_PUBLICA,
    ROLE_PROTOCOLO,
)

security = HTTPBearer()
ACCESS_PUBLICO = "publico"
ACCESS_INTERNO = "interno"
ACCESS_RESTRITO = "restrito"


def resolve_user_role(user: User) -> str:
    if user.role:
        return user.role
    return ROLE_ADMIN if user.is_admin else ROLE_CONSULTA_INTERNA


def is_admin_user(user: User) -> bool:
    return resolve_user_role(user) == ROLE_ADMIN or user.is_admin


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: Session = Depends(get_session),
):
    token = credentials.credentials
    payload = decode_access_token(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalido",
        )

    email = payload.get("sub")
    user = session.exec(select(User).where(User.email == email)).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario nao encontrado",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario inativo",
        )

    if is_admin_user(user) and user.role != ROLE_ADMIN:
        user.role = ROLE_ADMIN
        session.add(user)
        session.commit()
        session.refresh(user)

    return user


def require_roles(*allowed_roles: str):
    def _dependency(user: User = Depends(get_current_user)):
        role = resolve_user_role(user)
        if role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Perfil sem permissao para esta acao",
            )
        return user

    return _dependency


def require_admin(user: User = Depends(get_current_user)):
    if not is_admin_user(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso restrito a administradores",
        )
    return user


def require_document_writer(user: User = Depends(get_current_user)):
    role = resolve_user_role(user)
    if role not in {ROLE_ADMIN, ROLE_PROTOCOLO}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Somente perfis administrativos podem editar documentos",
        )
    return user


def can_read_access_level(user: User, access_level: str | None) -> bool:
    role = resolve_user_role(user)
    level = (access_level or ACCESS_INTERNO).strip().lower()
    valid_levels = {ACCESS_PUBLICO, ACCESS_INTERNO, ACCESS_RESTRITO}
    if level not in valid_levels:
        return False

    if role in {ROLE_ADMIN, ROLE_PROTOCOLO}:
        return True
    if role == ROLE_CONSULTA_PUBLICA:
        return level == ACCESS_PUBLICO
    if role == ROLE_CONSULTA_INTERNA:
        return level in {ACCESS_PUBLICO, ACCESS_INTERNO}
    return False


def require_access_level(user: User, access_level: str | None):
    if not can_read_access_level(user, access_level):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Perfil sem permissao para este nivel de acesso",
        )


def allowed_access_levels(user: User) -> set[str]:
    role = resolve_user_role(user)
    if role in {ROLE_ADMIN, ROLE_PROTOCOLO}:
        return {ACCESS_PUBLICO, ACCESS_INTERNO, ACCESS_RESTRITO}
    if role == ROLE_CONSULTA_PUBLICA:
        return {ACCESS_PUBLICO}
    return {ACCESS_PUBLICO, ACCESS_INTERNO}
