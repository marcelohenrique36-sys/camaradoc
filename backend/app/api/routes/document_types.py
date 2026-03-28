from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.api.deps import get_current_user, require_admin
from app.core.database import get_session
from app.models.document_type import DocumentType
from app.schemas.document_type import DocumentTypeCreate, DocumentTypeOut

router = APIRouter(prefix="/document-types", tags=["Tipos de Documento"])


@router.get("/", response_model=list[DocumentTypeOut])
def list_document_types(
    session: Session = Depends(get_session),
    user=Depends(get_current_user),
):
    return session.exec(select(DocumentType).order_by(DocumentType.name)).all()


@router.post("/", response_model=DocumentTypeOut)
def create_document_type(
    data: DocumentTypeCreate,
    session: Session = Depends(get_session),
    user=Depends(require_admin),
):
    existing = session.exec(
        select(DocumentType).where(DocumentType.name == data.name)
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="Tipo já cadastrado")

    item = DocumentType(name=data.name, description=data.description)
    session.add(item)
    session.commit()
    session.refresh(item)
    return item