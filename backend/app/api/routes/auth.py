from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func
from sqlmodel import Session, select

from app.api.deps import get_current_user, require_admin
from app.core.database import get_session
from app.core.security import create_access_token, get_password_hash, verify_password
from app.models.user import User
from app.schemas.auth import LoginRequest, Token
from app.schemas.user import (
    ROLE_ADMIN,
    ROLE_CONSULTA_INTERNA,
    UserCreate,
    UserOut,
    UserRoleUpdate,
    UserStatusUpdate,
    VALID_ROLES,
)
from app.services.audit_service import log_audit_event

router = APIRouter(prefix="/auth", tags=["Autenticacao"])


def _normalize_role(user_in: UserCreate) -> str:
    if user_in.role:
        role = user_in.role.strip()
        if role not in VALID_ROLES:
            raise HTTPException(status_code=400, detail="Perfil de usuario invalido")
        return role
    return ROLE_ADMIN if user_in.is_admin else ROLE_CONSULTA_INTERNA


@router.post("/register", response_model=UserOut)
def register(
    user_in: UserCreate,
    request: Request,
    session: Session = Depends(get_session),
    current_user=Depends(require_admin),
):
    existing = session.exec(select(User).where(User.email == user_in.email)).first()
    if existing:
        raise HTTPException(status_code=400, detail="E-mail ja cadastrado")

    role = _normalize_role(user_in)
    user = User(
        name=user_in.name,
        email=user_in.email,
        password_hash=get_password_hash(user_in.password),
        role=role,
        is_admin=(role == ROLE_ADMIN),
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    log_audit_event(
        session,
        action="user.create",
        entity_type="user",
        entity_id=str(user.id),
        user=current_user,
        request=request,
        details={"created_email": user.email, "role": role},
    )
    return user


@router.post("/login", response_model=Token)
def login(data: LoginRequest, request: Request, session: Session = Depends(get_session)):
    user = session.exec(select(User).where(User.email == data.email)).first()

    if not user or not verify_password(data.password, user.password_hash):
        log_audit_event(
            session,
            action="auth.login_failed",
            entity_type="user",
            entity_id=str(user.id) if user else None,
            user=user,
            request=request,
            details={"email": data.email},
        )
        raise HTTPException(status_code=401, detail="Credenciais invalidas")
    if not user.is_active:
        log_audit_event(
            session,
            action="auth.login_blocked",
            entity_type="user",
            entity_id=str(user.id),
            user=user,
            request=request,
            details={"reason": "inactive_user"},
        )
        raise HTTPException(status_code=403, detail="Usuario inativo")

    token = create_access_token(user.email)
    log_audit_event(
        session,
        action="auth.login",
        entity_type="user",
        entity_id=str(user.id),
        user=user,
        request=request,
    )
    return Token(access_token=token)


@router.get("/me", response_model=UserOut)
def me(user=Depends(get_current_user)):
    return user


@router.get("/users", response_model=list[UserOut])
def list_users(session: Session = Depends(get_session), user=Depends(require_admin)):
    return session.exec(select(User).order_by(User.created_at.desc())).all()


@router.patch("/users/{user_id}/role", response_model=UserOut)
def update_user_role(
    user_id: int,
    data: UserRoleUpdate,
    request: Request,
    session: Session = Depends(get_session),
    current_user=Depends(require_admin),
):
    role = data.role.strip()
    if role not in VALID_ROLES:
        raise HTTPException(status_code=400, detail="Perfil de usuario invalido")

    target = session.get(User, user_id)
    if not target:
        raise HTTPException(status_code=404, detail="Usuario nao encontrado")

    target.role = role
    target.is_admin = role == ROLE_ADMIN
    session.add(target)
    session.commit()
    session.refresh(target)

    log_audit_event(
        session,
        action="user.role.update",
        entity_type="user",
        entity_id=str(target.id),
        user=current_user,
        request=request,
        details={"target_email": target.email, "new_role": role},
    )
    return target


@router.patch("/users/{user_id}/status", response_model=UserOut)
def update_user_status(
    user_id: int,
    data: UserStatusUpdate,
    request: Request,
    session: Session = Depends(get_session),
    current_user=Depends(require_admin),
):
    target = session.get(User, user_id)
    if not target:
        raise HTTPException(status_code=404, detail="Usuario nao encontrado")
    if not data.is_active and target.id == current_user.id:
        raise HTTPException(status_code=400, detail="Nao e permitido inativar o proprio usuario")

    if not data.is_active and target.role == ROLE_ADMIN:
        other_active_admins = session.exec(
            select(func.count(User.id)).where(
                User.role == ROLE_ADMIN,
                User.is_active.is_(True),
                User.id != target.id,
            )
        ).one()
        if int(other_active_admins or 0) <= 0:
            raise HTTPException(
                status_code=400,
                detail="Nao e permitido inativar o ultimo administrador ativo",
            )

    target.is_active = data.is_active
    session.add(target)
    session.commit()
    session.refresh(target)

    log_audit_event(
        session,
        action="user.status.update",
        entity_type="user",
        entity_id=str(target.id),
        user=current_user,
        request=request,
        details={"target_email": target.email, "is_active": target.is_active},
    )
    return target
