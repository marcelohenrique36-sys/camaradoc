from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.api.deps import get_current_user, require_admin
from app.core.database import get_session
from app.models.sector import Sector
from app.schemas.sector import SectorCreate, SectorUpdate, SectorOut

router = APIRouter(prefix="/sectors", tags=["Setores"])


@router.get("/", response_model=list[SectorOut])
def list_sectors(
    session: Session = Depends(get_session),
    user=Depends(get_current_user),
):
    return session.exec(select(Sector).order_by(Sector.name)).all()


@router.post("/", response_model=SectorOut)
def create_sector(
    data: SectorCreate,
    session: Session = Depends(get_session),
    user=Depends(require_admin),
):
    existing = session.exec(select(Sector).where(Sector.name == data.name)).first()
    if existing:
        raise HTTPException(status_code=400, detail="Setor já cadastrado")

    sector = Sector(name=data.name, description=data.description)
    session.add(sector)
    session.commit()
    session.refresh(sector)
    return sector


@router.put("/{sector_id}", response_model=SectorOut)
def update_sector(
    sector_id: int,
    data: SectorUpdate,
    session: Session = Depends(get_session),
    user=Depends(require_admin),
):
    sector = session.get(Sector, sector_id)
    if not sector:
        raise HTTPException(status_code=404, detail="Setor não encontrado")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(sector, key, value)

    session.add(sector)
    session.commit()
    session.refresh(sector)
    return sector