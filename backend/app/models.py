"""
Modelos de Banco de Dados - Sistema de Arquivo Morto Digital
Conformidade LGPD - Lei Geral de Proteção de Dados
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

Base = declarative_base()


class TipoUsuario(str, enum.Enum):
    """Enum para tipos de usuário (RBAC)"""
    ADMINISTRADOR = "administrador"
    OPERADOR = "operador"
    CONSULTA = "consulta"


class TipoAcao(str, enum.Enum):
    """Enum para ações de auditoria"""
    LOGIN = "login"
    LOGOUT = "logout"
    UPLOAD = "upload"
    VISUALIZACAO = "visualizacao"
    DOWNLOAD = "download"
    EDICAO = "edicao"
    EXCLUSAO = "exclusao"
    BUSCA = "busca"


class Usuario(Base):
    """Tabela de Usuários com permissões RBAC"""
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    nome_completo = Column(String(200), nullable=False)
    email = Column(String(150), unique=True, nullable=False, index=True)
    senha_hash = Column(String(255), nullable=False)
    tipo_usuario = Column(SQLEnum(TipoUsuario), nullable=False, default=TipoUsuario.CONSULTA)
    cpf = Column(String(14), unique=True, nullable=False)
    ativo = Column(Integer, default=1)
    data_criacao = Column(DateTime, default=datetime.utcnow)
    ultima_atualizacao = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    documentos = relationship("Documento", back_populates="responsavel")
    logs = relationship("LogAuditoria", back_populates="usuario")

    def __repr__(self):
        return f"<Usuario(id={self.id}, nome='{self.nome_completo}', tipo='{self.tipo_usuario}')>"


class Documento(Base):
    """Tabela de Documentos Digitalizados"""
    __tablename__ = "documentos"

    id = Column(Integer, primary_key=True, index=True)
    titulo = Column(String(300), nullable=False, index=True)
    descricao = Column(Text)
    setor = Column(String(150), nullable=False, index=True)
    ano = Column(Integer, nullable=False, index=True)
    mes = Column(Integer, nullable=False)
    tipo_arquivo = Column(String(10), nullable=False)
    caminho_arquivo = Column(String(500), nullable=False, unique=True)
    tamanho_bytes = Column(Integer)
    texto_ocr = Column(Text, index=True)
    responsavel_upload_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    data_upload = Column(DateTime, default=datetime.utcnow, index=True)
    ultima_modificacao = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    responsavel = relationship("Usuario", back_populates="documentos")
    logs = relationship("LogAuditoria", back_populates="documento")

    def __repr__(self):
        return f"<Documento(id={self.id}, titulo='{self.titulo}', setor='{self.setor}')>"


class LogAuditoria(Base):
    """Tabela de Auditoria - Rastreamento obrigatório para conformidade legal"""
    __tablename__ = "logs_auditoria"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False, index=True)
    documento_id = Column(Integer, ForeignKey("documentos.id"), nullable=True, index=True)
    acao = Column(SQLEnum(TipoAcao), nullable=False, index=True)
    descricao = Column(Text)
    ip_origem = Column(String(50))
    data_hora = Column(DateTime, default=datetime.utcnow, index=True)

    usuario = relationship("Usuario", back_populates="logs")
    documento = relationship("Documento", back_populates="logs")

    def __repr__(self):
        return f"<LogAuditoria(id={self.id}, usuario_id={self.usuario_id}, acao='{self.acao}')>"
