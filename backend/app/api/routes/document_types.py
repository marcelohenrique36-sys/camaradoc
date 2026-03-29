from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlmodel import Session, select

from app.api.deps import get_current_user, require_admin
from app.core.database import get_session
from app.models.document import Document
from app.models.document_type import DocumentType
from app.schemas.document_type import DocumentTypeCreate, DocumentTypeOut, DocumentTypeUpdate
from app.services.audit_service import log_audit_event

router = APIRouter(prefix="/document-types", tags=["Tipos de Documento"])


@router.get("/", response_model=list[DocumentTypeOut])
def list_document_types(
    session: Session = Depends(get_session),
    user=Depends(get_current_user),
    include_inactive: bool = Query(default=False),
):
    statement = select(DocumentType)
    if not include_inactive:
        statement = statement.where(DocumentType.is_active.is_(True))
    statement = statement.order_by(DocumentType.name)
    return session.exec(statement).all()


@router.post("/", response_model=DocumentTypeOut)
def create_document_type(
    data: DocumentTypeCreate,
    request: Request,
    session: Session = Depends(get_session),
    user=Depends(require_admin),
):
    existing = session.exec(
        select(DocumentType).where(DocumentType.name == data.name)
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Tipo ja cadastrado")

    item = DocumentType(name=data.name, description=data.description)
    session.add(item)
    session.commit()
    session.refresh(item)

    log_audit_event(
        session,
        action="document_type.create",
        entity_type="document_type",
        entity_id=str(item.id),
        user=user,
        request=request,
        details={"name": item.name},
    )
    return item


@router.put("/{document_type_id}", response_model=DocumentTypeOut)
def update_document_type(
    document_type_id: int,
    data: DocumentTypeUpdate,
    request: Request,
    session: Session = Depends(get_session),
    user=Depends(require_admin),
):
    item = session.get(DocumentType, document_type_id)
    if not item:
        raise HTTPException(status_code=404, detail="Tipo de documento nao encontrado")

    updates = data.model_dump(exclude_unset=True)

    if "name" in updates:
        duplicate = session.exec(
            select(DocumentType).where(
                DocumentType.name == updates["name"],
                DocumentType.id != document_type_id,
            )
        ).first()
        if duplicate:
            raise HTTPException(status_code=400, detail="Nome de tipo ja em uso")

    for key, value in updates.items():
        setattr(item, key, value)

    session.add(item)
    session.commit()
    session.refresh(item)

    log_audit_event(
        session,
        action="document_type.update",
        entity_type="document_type",
        entity_id=str(item.id),
        user=user,
        request=request,
        details={"fields": sorted(list(updates.keys()))},
    )
    return item


@router.delete("/{document_type_id}", response_model=DocumentTypeOut)
def disable_document_type(
    document_type_id: int,
    request: Request,
    session: Session = Depends(get_session),
    user=Depends(require_admin),
):
    item = session.get(DocumentType, document_type_id)
    if not item:
        raise HTTPException(status_code=404, detail="Tipo de documento nao encontrado")

    in_use = session.exec(
        select(Document).where(Document.document_type_id == document_type_id).limit(1)
    ).first()
    if in_use:
        item.is_active = False
    else:
        item.is_active = False

    session.add(item)
    session.commit()
    session.refresh(item)

    log_audit_event(
        session,
        action="document_type.disable",
        entity_type="document_type",
        entity_id=str(item.id),
        user=user,
        request=request,
    )
    return item
