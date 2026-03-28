from contextlib import asynccontextmanager
from fastapi import FastAPI
from sqlmodel import select

from app.core.config import settings
from app.core.database import init_db, get_session
from app.core.security import get_password_hash
from app.models import User
from app.services.file_service import ensure_directories

from app.api.routes.auth import router as auth_router
from app.api.routes.sectors import router as sectors_router
from app.api.routes.document_types import router as document_types_router
from app.api.routes.documents import router as documents_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_directories()
    init_db()

    session = next(get_session())
    try:
        admin = session.exec(
            select(User).where(User.email == "admin@camaradoc.local")
        ).first()

        if not admin:
            admin = User(
                name="Administrador",
                email="admin@camaradoc.local",
                password_hash=get_password_hash("123456"),
                is_admin=True,
            )
            session.add(admin)
            session.commit()
    finally:
        session.close()

    yield


app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)

app.include_router(auth_router)
app.include_router(sectors_router)
app.include_router(document_types_router)
app.include_router(documents_router)


@app.get("/")
def root():
    return {"message": "CamaraDOC API online"}


@app.get("/health")
def health():
    return {"status": "ok"}