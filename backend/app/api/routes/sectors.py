from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlmodel import Session, select

from app.api.deps import get_current_user, require_admin
from app.core.database import get_session
from app.models.document import Document
from app.models.sector import Sector
from app.schemas.sector import SectorCreate, SectorOut, SectorUpdate
from app.services.audit_service import log_audit_event

router = APIRouter(prefix="/sectors", tags=["Setores"])


@router.get("/", response_model=list[SectorOut])
def list_sectors(
    session: Session = Depends(get_session),
    user=Depends(get_current_user),
    include_inactive: bool = Query(default=False),
):
    statement = select(Sector)
    if not include_inactive:
        statement = statement.where(Sector.is_active.is_(True))
    statement = statement.order_by(Sector.name)
    return session.exec(statement).all()


@router.post("/", response_model=SectorOut)
def create_sector(
    data: SectorCreate,
    request: Request,
    session: Session = Depends(get_session),
    user=Depends(require_admin),
):
    existing = session.exec(select(Sector).where(Sector.name == data.name)).first()
    if existing:
        raise HTTPException(status_code=400, detail="Setor ja cadastrado")

    sector = Sector(name=data.name, description=data.description)
    session.add(sector)
    session.commit()
    session.refresh(sector)

    log_audit_event(
        session,
        action="sector.create",
        entity_type="sector",
        entity_id=str(sector.id),
        user=user,
        request=request,
        details={"name": sector.name},
    )
    return sector


@router.put("/{sector_id}", response_model=SectorOut)
def update_sector(
    sector_id: int,
    data: SectorUpdate,
    request: Request,
    session: Session = Depends(get_session),
    user=Depends(require_admin),
):
    sector = session.get(Sector, sector_id)
    if not sector:
        raise HTTPException(status_code=404, detail="Setor nao encontrado")

    updates = data.model_dump(exclude_unset=True)

    if "name" in updates:
        duplicate = session.exec(
            select(Sector).where(Sector.name == updates["name"], Sector.id != sector_id)
        ).first()
        if duplicate:
            raise HTTPException(status_code=400, detail="Nome de setor ja em uso")

    for key, value in updates.items():
        setattr(sector, key, value)

    session.add(sector)
    session.commit()
    session.refresh(sector)

    log_audit_event(
        session,
        action="sector.update",
        entity_type="sector",
        entity_id=str(sector.id),
        user=user,
        request=request,
        details={"fields": sorted(list(updates.keys()))},
    )
    return sector


@router.delete("/{sector_id}", response_model=SectorOut)
def disable_sector(
    sector_id: int,
    request: Request,
    session: Session = Depends(get_session),
    user=Depends(require_admin),
):
    sector = session.get(Sector, sector_id)
    if not sector:
        raise HTTPException(status_code=404, detail="Setor nao encontrado")

    in_use = session.exec(
        select(Document).where(Document.sector_id == sector_id).limit(1)
    ).first()
    if in_use:
        sector.is_active = False
    else:
        sector.is_active = False

    session.add(sector)
    session.commit()
    session.refresh(sector)

    log_audit_event(
        session,
        action="sector.disable",
        entity_type="sector",
        entity_id=str(sector.id),
        user=user,
        request=request,
    )
    return sector
