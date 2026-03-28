from datetime import datetime
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlmodel import Session, select

from app.api.deps import get_current_user
from app.core.database import get_session
from app.models.document import Document
from app.schemas.document import DocumentOut
from app.services.file_service import save_uploaded_pdf

router = APIRouter(prefix="/documents", tags=["Documentos"])


@router.get("/", response_model=list[DocumentOut])
def list_documents(
    session: Session = Depends(get_session),
    user=Depends(get_current_user),
):
    return session.exec(select(Document).order_by(Document.created_at.desc())).all()


@router.post("/upload", response_model=DocumentOut)
def upload_document(
    title: str = Form(...),
    document_type_id: int = Form(...),
    sector_id: int = Form(...),
    number: str | None = Form(default=None),
    year: int | None = Form(default=None),
    document_date: str | None = Form(default=None),
    author_origin: str | None = Form(default=None),
    subject: str | None = Form(default=None),
    keywords: str | None = Form(default=None),
    access_level: str = Form(default="interno"),
    status: str = Form(default="ativo"),
    notes: str | None = Form(default=None),
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
    user=Depends(get_current_user),
):
    try:
        original_file_path = save_uploaded_pdf(file)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    parsed_date = None
    if document_date:
        parsed_date = datetime.strptime(document_date, "%Y-%m-%d").date()

    doc = Document(
        title=title,
        document_type_id=document_type_id,
        number=number,
        year=year,
        document_date=parsed_date,
        sector_id=sector_id,
        author_origin=author_origin,
        subject=subject,
        keywords=keywords,
        access_level=access_level,
        status=status,
        notes=notes,
        original_file_path=original_file_path,
        created_by=user.id,
    )

    session.add(doc)
    session.commit()
    session.refresh(doc)
    return doc