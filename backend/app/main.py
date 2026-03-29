"""
API Principal - Sistema de Arquivo Morto Digital
FastAPI com autenticação JWT e RBAC
"""

from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, or_
from sqlalchemy.orm import sessionmaker, Session
from passlib.context import CryptContext
from datetime import datetime, timedelta
from typing import List, Optional
import jwt
import os
import shutil
from pydantic import BaseModel, EmailStr

from models import Base, Usuario, Documento, LogAuditoria, TipoUsuario, TipoAcao
from ocr_engine import OCREngine

SECRET_KEY = os.getenv("SECRET_KEY", "sua-chave-secreta-muito-segura-aqui-troque-em-producao")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 480

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://arquivo_user:senha_segura@db:5432/arquivo_morto")
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "/app/uploads")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

app = FastAPI(title="Arquivo Morto Digital", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ocr_engine = OCREngine()


def get_db():
    """Dependency para obter sessão do banco de dados"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def criar_usuario_admin_padrao(db: Session):
    """Cria usuário administrador padrão se não existir"""
    admin = db.query(Usuario).filter(Usuario.email == "admin@camara.gov.br").first()
    if not admin:
        admin = Usuario(
            nome_completo="Administrador do Sistema",
            email="admin@camara.gov.br",
            senha_hash=pwd_context.hash("admin123"),
            tipo_usuario=TipoUsuario.ADMINISTRADOR,
            cpf="000.000.000-00"
        )
        db.add(admin)
        db.commit()


with SessionLocal() as db:
    criar_usuario_admin_padrao(db)


class UsuarioLogin(BaseModel):
    email: EmailStr
    senha: str


class UsuarioCriar(BaseModel):
    nome_completo: str
    email: EmailStr
    senha: str
    tipo_usuario: TipoUsuario
    cpf: str


class DocumentoResposta(BaseModel):
    id: int
    titulo: str
    descricao: Optional[str]
    setor: str
    ano: int
    mes: int
    tipo_arquivo: str
    data_upload: datetime
    responsavel_nome: str

    class Config:
        from_attributes = True


def criar_token_acesso(data: dict):
    """Cria token JWT"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def verificar_token(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    """Verifica token JWT e retorna usuário"""
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Token inválido")
        
        usuario = db.query(Usuario).filter(Usuario.email == email).first()
        if usuario is None:
            raise HTTPException(status_code=401, detail="Usuário não encontrado")
        
        return usuario
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expirado")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Token inválido")


async def registrar_log(db: Session, usuario_id: int, acao: TipoAcao, documento_id: Optional[int] = None, descricao: Optional[str] = None, ip: Optional[str] = None):
    """Registra ação no log de auditoria"""
    log = LogAuditoria(
        usuario_id=usuario_id,
        documento_id=documento_id,
        acao=acao,
        descricao=descricao,
        ip_origem=ip
    )
    db.add(log)
    db.commit()


@app.post("/api/login")
async def login(credenciais: UsuarioLogin, request: Request, db: Session = Depends(get_db)):
    """Endpoint de login com JWT"""
    usuario = db.query(Usuario).filter(Usuario.email == credenciais.email).first()
    
    if not usuario or not pwd_context.verify(credenciais.senha, usuario.senha_hash):
        raise HTTPException(status_code=401, detail="Credenciais inválidas")
    
    if not usuario.ativo:
        raise HTTPException(status_code=403, detail="Usuário desativado")
    
    await registrar_log(db, usuario.id, TipoAcao.LOGIN, ip=request.client.host)
    
    token = criar_token_acesso({"sub": usuario.email})
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "usuario": {
            "id": usuario.id,
            "nome": usuario.nome_completo,
            "email": usuario.email,
            "tipo": usuario.tipo_usuario.value
        }
    }


@app.post("/api/usuarios", status_code=status.HTTP_201_CREATED)
async def criar_usuario(usuario_data: UsuarioCriar, usuario_atual: Usuario = Depends(verificar_token), db: Session = Depends(get_db)):
    """Criar novo usuário (apenas Administradores)"""
    if usuario_atual.tipo_usuario != TipoUsuario.ADMINISTRADOR:
        raise HTTPException(status_code=403, detail="Acesso negado")
    
    if db.query(Usuario).filter(Usuario.email == usuario_data.email).first():
        raise HTTPException(status_code=400, detail="Email já cadastrado")
    
    if db.query(Usuario).filter(Usuario.cpf == usuario_data.cpf).first():
        raise HTTPException(status_code=400, detail="CPF já cadastrado")
    
    novo_usuario = Usuario(
        nome_completo=usuario_data.nome_completo,
        email=usuario_data.email,
        senha_hash=pwd_context.hash(usuario_data.senha),
        tipo_usuario=usuario_data.tipo_usuario,
        cpf=usuario_data.cpf
    )
    
    db.add(novo_usuario)
    db.commit()
    db.refresh(novo_usuario)
    
    return {"id": novo_usuario.id, "mensagem": "Usuário criado com sucesso"}


@app.get("/api/usuarios")
async def listar_usuarios(usuario_atual: Usuario = Depends(verificar_token), db: Session = Depends(get_db)):
    """Lista todos os usuários (apenas Administradores)"""
    if usuario_atual.tipo_usuario != TipoUsuario.ADMINISTRADOR:
        raise HTTPException(status_code=403, detail="Acesso negado")
    
    usuarios = db.query(Usuario).all()
    return [
        {
            "id": u.id,
            "nome_completo": u.nome_completo,
            "email": u.email,
            "tipo_usuario": u.tipo_usuario.value,
            "ativo": u.ativo
        }
        for u in usuarios
    ]


@app.post("/api/documentos/upload")
async def upload_documento(
    request: Request,
    arquivo: UploadFile = File(...),
    titulo: str = None,
    descricao: str = None,
    setor: str = None,
    usuario_atual: Usuario = Depends(verificar_token),
    db: Session = Depends(get_db)
):
    """Upload de documento com OCR automático"""
    if usuario_atual.tipo_usuario == TipoUsuario.CONSULTA:
        raise HTTPException(status_code=403, detail="Permissão insuficiente")
    
    extensao = os.path.splitext(arquivo.filename)[1].lower()
    if extensao not in [".pdf", ".jpg", ".jpeg", ".png"]:
        raise HTTPException(status_code=400, detail="Formato não suportado")
    
    agora = datetime.now()
    ano = agora.year
    mes = agora.month
    
    pasta_destino = os.path.join(UPLOAD_DIR, str(ano), f"{mes:02d}", setor or "Geral")
    os.makedirs(pasta_destino, exist_ok=True)
    
    nome_arquivo = f"{agora.strftime('%Y%m%d_%H%M%S')}_{arquivo.filename}"
    caminho_completo = os.path.join(pasta_destino, nome_arquivo)
    
    with open(caminho_completo, "wb") as buffer:
        shutil.copyfileobj(arquivo.file, buffer)
    
    texto_ocr = ocr_engine.processar_documento(caminho_completo)
    
    documento = Documento(
        titulo=titulo or arquivo.filename,
        descricao=descricao,
        setor=setor or "Geral",
        ano=ano,
        mes=mes,
        tipo_arquivo=extensao,
        caminho_arquivo=caminho_completo,
        tamanho_bytes=os.path.getsize(caminho_completo),
        texto_ocr=texto_ocr,
        responsavel_upload_id=usuario_atual.id
    )
    
    db.add(documento)
    db.commit()
    db.refresh(documento)
    
    await registrar_log(db, usuario_atual.id, TipoAcao.UPLOAD, documento.id, f"Upload: {titulo}", request.client.host)
    
    return {"id": documento.id, "mensagem": "Documento enviado com sucesso", "texto_extraido": len(texto_ocr or "") > 0}


@app.get("/api/documentos/buscar")
async def buscar_documentos(
    request: Request,
    q: str,
    usuario_atual: Usuario = Depends(verificar_token),
    db: Session = Depends(get_db)
):
    """Busca inteligente por conteúdo OCR"""
    termo_busca = f"%{q}%"
    
    documentos = db.query(Documento).filter(
        or_(
            Documento.titulo.ilike(termo_busca),
            Documento.texto_ocr.ilike(termo_busca),
            Documento.descricao.ilike(termo_busca)
        )
    ).all()
    
    await registrar_log(db, usuario_atual.id, TipoAcao.BUSCA, descricao=f"Busca: {q}", ip=request.client.host)
    
    return [
        {
            "id": doc.id,
            "titulo": doc.titulo,
            "descricao": doc.descricao,
            "setor": doc.setor,
            "ano": doc.ano,
            "mes": doc.mes,
            "tipo_arquivo": doc.tipo_arquivo,
            "data_upload": doc.data_upload,
            "responsavel_nome": doc.responsavel.nome_completo
        }
        for doc in documentos
    ]


@app.get("/api/logs")
async def listar_logs(usuario_atual: Usuario = Depends(verificar_token), db: Session = Depends(get_db)):
    """Lista logs de auditoria (apenas Administradores)"""
    if usuario_atual.tipo_usuario != TipoUsuario.ADMINISTRADOR:
        raise HTTPException(status_code=403, detail="Acesso negado")
    
    logs = db.query(LogAuditoria).order_by(LogAuditoria.data_hora.desc()).limit(100).all()
    
    return [
        {
            "id": log.id,
            "usuario": log.usuario.nome_completo,
            "acao": log.acao.value,
            "descricao": log.descricao,
            "ip_origem": log.ip_origem,
            "data_hora": log.data_hora
        }
        for log in logs
    ]


@app.get("/")
async def root():
    """Health check"""
    return {"status": "online", "sistema": "Arquivo Morto Digital", "versao": "1.0.0"}
