import os
from datetime import date, datetime
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import desc, func
from sqlmodel import Session, select

from app.api.deps import (
    allowed_access_levels,
    require_access_level,
    ROLE_ADMIN,
    get_current_user,
    require_admin,
    require_document_writer,
    resolve_user_role,
)
from app.core.database import get_session
from app.models.document import Document
from app.models.document_type import DocumentType
from app.models.sector import Sector
from app.schemas.document import DocumentOut, DocumentUpdate
from app.services.audit_service import log_audit_event
from app.services.file_service import resolve_storage_path, save_uploaded_pdf

router = APIRouter(prefix="/documents", tags=["Documentos"])
ALLOWED_ACCESS_LEVELS = {"publico", "interno", "restrito"}
ALLOWED_STATUS = {"ativo", "inativo"}
ALLOWED_OCR_STATUS = {"pending", "processing", "done", "error"}


def _parse_document_date(document_date: str | None) -> date | None:
    if not document_date:
        return None

    try:
        return datetime.strptime(document_date, "%Y-%m-%d").date()
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail="document_date deve estar no formato YYYY-MM-DD",
        ) from exc


def _safe_filename(title: str, document_id: int, suffix: str = "") -> str:
    normalized = "".join(ch if ch.isalnum() else "_" for ch in title).strip("_")
    if not normalized:
        normalized = "documento"
    extra = f"_{suffix}" if suffix else ""
    return f"{normalized}_{document_id}{extra}.pdf"


def _normalize_access_level(access_level: str | None) -> str | None:
    if access_level is None:
        return None
    normalized = access_level.strip().lower()
    if normalized not in ALLOWED_ACCESS_LEVELS:
        raise HTTPException(status_code=400, detail="access_level invalido")
    return normalized


def _normalize_status(status_value: str | None) -> str | None:
    if status_value is None:
        return None
    normalized = status_value.strip().lower()
    if normalized not in ALLOWED_STATUS:
        raise HTTPException(status_code=400, detail="status invalido")
    return normalized


def _normalize_ocr_status(ocr_status: str | None) -> str | None:
    if ocr_status is None:
        return None
    normalized = ocr_status.strip().lower()
    if normalized not in ALLOWED_OCR_STATUS:
        raise HTTPException(status_code=400, detail="ocr_status invalido")
    return normalized


def _assert_document_permission(document: Document, user):
    require_access_level(user, document.access_level)


def _apply_visibility_filter(statement, user, include_inactive: bool):
    role = resolve_user_role(user)

    if role == ROLE_ADMIN:
        if not include_inactive:
            statement = statement.where(func.coalesce(Document.status, "ativo") != "inativo")
        return statement

    allowed_levels = tuple(allowed_access_levels(user))
    statement = statement.where(func.coalesce(Document.status, "ativo") != "inativo")
    statement = statement.where(
        func.coalesce(Document.access_level, "interno").in_(allowed_levels)
    )
    return statement


def _run_document_search(
    session: Session,
    user,
    q: str | None,
    number: str | None,
    year: int | None,
    title: str | None,
    subject: str | None,
    author_origin: str | None,
    document_type_id: int | None,
    sector_id: int | None,
    ocr_status: str | None,
    access_level: str | None,
    status: str | None,
    include_inactive: bool,
    limit: int,
    offset: int,
):
    statement = _apply_visibility_filter(select(Document), user, include_inactive)

    if number:
        statement = statement.where(Document.number.ilike(f"%{number.strip()}%"))
    if year is not None:
        statement = statement.where(Document.year == year)
    if title:
        statement = statement.where(Document.title.ilike(f"%{title.strip()}%"))
    if subject:
        statement = statement.where(Document.subject.ilike(f"%{subject.strip()}%"))
    if author_origin:
        statement = statement.where(
            Document.author_origin.ilike(f"%{author_origin.strip()}%")
        )
    if document_type_id is not None:
        statement = statement.where(Document.document_type_id == document_type_id)
    if sector_id is not None:
        statement = statement.where(Document.sector_id == sector_id)
    normalized_ocr_status = _normalize_ocr_status(ocr_status)
    normalized_access_level = _normalize_access_level(access_level)
    normalized_status = _normalize_status(status)

    if normalized_ocr_status:
        statement = statement.where(Document.ocr_status == normalized_ocr_status)
    if normalized_access_level:
        statement = statement.where(Document.access_level == normalized_access_level)
    if normalized_status:
        statement = statement.where(Document.status == normalized_status)

    if q and q.strip():
        cleaned_query = q.strip()
        ts_query = func.websearch_to_tsquery("portuguese", cleaned_query)
        search_vector = func.to_tsvector(
            "portuguese",
            func.concat_ws(
                " ",
                func.coalesce(Document.number, ""),
                func.coalesce(Document.title, ""),
                func.coalesce(Document.subject, ""),
                func.coalesce(Document.author_origin, ""),
                func.coalesce(Document.keywords, ""),
                func.coalesce(Document.extracted_text, ""),
            ),
        )
        rank_score = func.ts_rank_cd(search_vector, ts_query)
        statement = statement.where(search_vector.op("@@")(ts_query)).order_by(
            desc(rank_score),
            Document.created_at.desc(),
        )
    else:
        statement = statement.order_by(Document.created_at.desc())

    statement = statement.offset(offset).limit(limit)
    return session.exec(statement).all()


def _resolve_document_file(
    document: Document,
    *,
    prefer_ocr: bool,
    require_ocr: bool = False,
) -> str:
    selected_path = document.ocr_file_path if prefer_ocr else document.original_file_path
    if prefer_ocr and not selected_path:
        selected_path = document.original_file_path if not require_ocr else None

    safe_path = resolve_storage_path(selected_path or "")
    if not safe_path or not os.path.exists(safe_path):
        raise HTTPException(status_code=404, detail="Arquivo do documento nao encontrado")
    return safe_path


def _validate_document_refs(
    session: Session,
    *,
    document_type_id: int | None = None,
    sector_id: int | None = None,
):
    if document_type_id is not None:
        doc_type = session.get(DocumentType, document_type_id)
        if not doc_type or not doc_type.is_active:
            raise HTTPException(
                status_code=400,
                detail="document_type_id nao encontrado ou inativo",
            )
    if sector_id is not None:
        sector = session.get(Sector, sector_id)
        if not sector or not sector.is_active:
            raise HTTPException(
                status_code=400,
                detail="sector_id nao encontrado ou inativo",
            )


@router.get("/stats")
def document_stats(
    session: Session = Depends(get_session),
    user=Depends(get_current_user),
):
    base = _apply_visibility_filter(select(Document), user, include_inactive=False)
    documents = session.exec(base).all()

    total = len(documents)
    by_ocr_status: dict[str, int] = {}
    for doc in documents:
        key = doc.ocr_status or "pending"
        by_ocr_status[key] = by_ocr_status.get(key, 0) + 1

    return {
        "total_documents": total,
        "ocr_status": by_ocr_status,
    }


@router.get("/", response_model=list[DocumentOut])
def list_documents(
    session: Session = Depends(get_session),
    user=Depends(get_current_user),
    q: str | None = Query(default=None, min_length=2),
    number: str | None = None,
    year: int | None = None,
    title: str | None = None,
    subject: str | None = None,
    author_origin: str | None = None,
    document_type_id: int | None = None,
    sector_id: int | None = None,
    ocr_status: str | None = None,
    access_level: str | None = None,
    status: str | None = None,
    include_inactive: bool = Query(default=False),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    return _run_document_search(
        session=session,
        user=user,
        q=q,
        number=number,
        year=year,
        title=title,
        subject=subject,
        author_origin=author_origin,
        document_type_id=document_type_id,
        sector_id=sector_id,
        ocr_status=ocr_status,
        access_level=access_level,
        status=status,
        include_inactive=include_inactive,
        limit=limit,
        offset=offset,
    )


@router.get("/search", response_model=list[DocumentOut])
def search_documents(
    session: Session = Depends(get_session),
    user=Depends(get_current_user),
    q: str | None = Query(default=None, min_length=2),
    number: str | None = None,
    year: int | None = None,
    title: str | None = None,
    subject: str | None = None,
    author_origin: str | None = None,
    document_type_id: int | None = None,
    sector_id: int | None = None,
    ocr_status: str | None = None,
    access_level: str | None = None,
    status: str | None = None,
    include_inactive: bool = Query(default=False),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    return _run_document_search(
        session=session,
        user=user,
        q=q,
        number=number,
        year=year,
        title=title,
        subject=subject,
        author_origin=author_origin,
        document_type_id=document_type_id,
        sector_id=sector_id,
        ocr_status=ocr_status,
        access_level=access_level,
        status=status,
        include_inactive=include_inactive,
        limit=limit,
        offset=offset,
    )


@router.get("/{document_id}", response_model=DocumentOut)
def get_document(
    document_id: int,
    session: Session = Depends(get_session),
    user=Depends(get_current_user),
):
    document = session.get(Document, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Documento nao encontrado")
    _assert_document_permission(document, user)
    if document.status == "inativo" and resolve_user_role(user) != ROLE_ADMIN:
        raise HTTPException(status_code=404, detail="Documento nao encontrado")
    return document


@router.post("/upload", response_model=DocumentOut)
def upload_document(
    request: Request,
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
    user=Depends(require_document_writer),
):
    role = resolve_user_role(user)
    access_level = _normalize_access_level(access_level) or "interno"
    status = _normalize_status(status) or "ativo"

    _validate_document_refs(
        session,
        document_type_id=document_type_id,
        sector_id=sector_id,
    )

    require_access_level(user, access_level)
    if role != ROLE_ADMIN:
        status = "ativo"

    try:
        original_file_path = save_uploaded_pdf(file)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    parsed_date = _parse_document_date(document_date)

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
        ocr_status="pending",
        ocr_error=None,
    )

    session.add(doc)
    session.commit()
    session.refresh(doc)

    log_audit_event(
        session,
        action="document.upload",
        entity_type="document",
        entity_id=str(doc.id),
        user=user,
        request=request,
        details={"title": doc.title, "access_level": doc.access_level},
    )
    return doc


@router.put("/{document_id}", response_model=DocumentOut)
def update_document(
    document_id: int,
    data: DocumentUpdate,
    request: Request,
    session: Session = Depends(get_session),
    user=Depends(require_document_writer),
):
    document = session.get(Document, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Documento nao encontrado")

    role = resolve_user_role(user)
    updates = data.model_dump(exclude_unset=True)
    if "access_level" in updates:
        updates["access_level"] = _normalize_access_level(updates.get("access_level"))
        if updates["access_level"] is None:
            raise HTTPException(status_code=400, detail="access_level invalido")
    if "status" in updates:
        updates["status"] = _normalize_status(updates.get("status"))
        if updates["status"] is None:
            raise HTTPException(status_code=400, detail="status invalido")

    if role != ROLE_ADMIN:
        forbidden = {"document_type_id", "sector_id", "access_level", "status"}
        if forbidden.intersection(set(updates.keys())):
            raise HTTPException(
                status_code=403,
                detail="Perfil atual nao pode alterar tipo/setor/status/access_level",
            )

    _validate_document_refs(
        session,
        document_type_id=updates.get("document_type_id"),
        sector_id=updates.get("sector_id"),
    )

    for key, value in updates.items():
        setattr(document, key, value)

    session.add(document)
    session.commit()
    session.refresh(document)

    log_audit_event(
        session,
        action="document.update",
        entity_type="document",
        entity_id=str(document.id),
        user=user,
        request=request,
        details={"fields": sorted(list(updates.keys()))},
    )
    return document


@router.post("/{document_id}/replace-file", response_model=DocumentOut)
def replace_document_file(
    document_id: int,
    request: Request,
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
    user=Depends(require_document_writer),
):
    document = session.get(Document, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Documento nao encontrado")

    try:
        new_path = save_uploaded_pdf(file)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    document.original_file_path = new_path
    document.ocr_file_path = None
    document.extracted_text = None
    document.ocr_status = "pending"
    document.ocr_error = None

    session.add(document)
    session.commit()
    session.refresh(document)

    log_audit_event(
        session,
        action="document.replace_file",
        entity_type="document",
        entity_id=str(document.id),
        user=user,
        request=request,
    )
    return document


@router.delete("/{document_id}", response_model=DocumentOut)
def disable_document(
    document_id: int,
    request: Request,
    session: Session = Depends(get_session),
    user=Depends(require_admin),
):
    document = session.get(Document, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Documento nao encontrado")

    document.status = "inativo"
    session.add(document)
    session.commit()
    session.refresh(document)

    log_audit_event(
        session,
        action="document.disable",
        entity_type="document",
        entity_id=str(document.id),
        user=user,
        request=request,
    )
    return document


def _stream_document(
    *,
    document: Document,
    user,
    session: Session,
    request: Request,
    action: str,
    prefer_ocr: bool,
    require_ocr: bool,
    filename_suffix: str = "",
    inline: bool = False,
):
    _assert_document_permission(document, user)
    if document.status == "inativo" and resolve_user_role(user) != ROLE_ADMIN:
        raise HTTPException(status_code=404, detail="Documento nao encontrado")

    safe_path = _resolve_document_file(
        document, prefer_ocr=prefer_ocr, require_ocr=require_ocr
    )
    filename = _safe_filename(document.title, document.id, suffix=filename_suffix)

    log_audit_event(
        session,
        action=action,
        entity_type="document",
        entity_id=str(document.id),
        user=user,
        request=request,
    )

    if inline:
        return FileResponse(
            path=safe_path,
            media_type="application/pdf",
            headers={"Content-Disposition": f'inline; filename="{filename}"'},
        )
    return FileResponse(
        path=safe_path,
        media_type="application/pdf",
        filename=filename,
    )


@router.get("/{document_id}/download")
def download_document(
    document_id: int,
    request: Request,
    session: Session = Depends(get_session),
    user=Depends(get_current_user),
):
    document = session.get(Document, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Documento nao encontrado")
    return _stream_document(
        document=document,
        user=user,
        session=session,
        request=request,
        action="document.download",
        prefer_ocr=True,
        require_ocr=False,
    )


@router.get("/{document_id}/download/original")
def download_document_original(
    document_id: int,
    request: Request,
    session: Session = Depends(get_session),
    user=Depends(get_current_user),
):
    document = session.get(Document, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Documento nao encontrado")
    return _stream_document(
        document=document,
        user=user,
        session=session,
        request=request,
        action="document.download_original",
        prefer_ocr=False,
        require_ocr=False,
        filename_suffix="original",
    )


@router.get("/{document_id}/download/ocr")
def download_document_ocr(
    document_id: int,
    request: Request,
    session: Session = Depends(get_session),
    user=Depends(get_current_user),
):
    document = session.get(Document, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Documento nao encontrado")
    return _stream_document(
        document=document,
        user=user,
        session=session,
        request=request,
        action="document.download_ocr",
        prefer_ocr=True,
        require_ocr=True,
        filename_suffix="ocr",
    )


@router.get("/{document_id}/view")
def view_document(
    document_id: int,
    request: Request,
    session: Session = Depends(get_session),
    user=Depends(get_current_user),
):
    document = session.get(Document, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Documento nao encontrado")
    return _stream_document(
        document=document,
        user=user,
        session=session,
        request=request,
        action="document.view",
        prefer_ocr=True,
        require_ocr=False,
        inline=True,
    )


@router.post("/{document_id}/reprocess-ocr", response_model=DocumentOut)
def reprocess_ocr(
    document_id: int,
    request: Request,
    session: Session = Depends(get_session),
    user=Depends(require_document_writer),
):
    document = session.get(Document, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Documento nao encontrado")

    document.ocr_status = "pending"
    document.ocr_file_path = None
    document.extracted_text = None
    document.ocr_error = None
    session.add(document)
    session.commit()
    session.refresh(document)

    log_audit_event(
        session,
        action="document.reprocess_ocr",
        entity_type="document",
        entity_id=str(document.id),
        user=user,
        request=request,
    )
    return document
