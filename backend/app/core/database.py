import logging
from sqlmodel import SQLModel, Session, create_engine
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL, echo=False)
logger = logging.getLogger(__name__)


def get_session():
    with Session(engine) as session:
        yield session


def init_db():
    SQLModel.metadata.create_all(engine)
    _create_document_indexes()


def _create_document_indexes():
    statements = [
        'ALTER TABLE "user" ADD COLUMN IF NOT EXISTS role VARCHAR(64);',
        "UPDATE \"user\" SET role = 'admin' WHERE COALESCE(is_admin, false) = true AND (role IS NULL OR role = '');",
        "UPDATE \"user\" SET role = 'consulta_interna' WHERE role IS NULL OR role = '';",
        'CREATE INDEX IF NOT EXISTS idx_user_role ON "user" (role);',
        "ALTER TABLE document ADD COLUMN IF NOT EXISTS ocr_error TEXT;",
        "UPDATE document SET ocr_status = 'done' WHERE ocr_status = 'completed';",
        "UPDATE document SET ocr_status = 'error' WHERE ocr_status = 'failed';",
        """
        CREATE INDEX IF NOT EXISTS idx_document_search_tsv
        ON document
        USING GIN (
            to_tsvector(
                'portuguese',
                concat_ws(
                    ' ',
                    coalesce(number, ''),
                    coalesce(title, ''),
                    coalesce(subject, ''),
                    coalesce(author_origin, ''),
                    coalesce(keywords, ''),
                    coalesce(extracted_text, '')
                )
            )
        );
        """,
        "CREATE INDEX IF NOT EXISTS idx_document_year ON document (year);",
        "CREATE INDEX IF NOT EXISTS idx_document_created_at ON document (created_at DESC);",
        "CREATE INDEX IF NOT EXISTS idx_document_access_level ON document (access_level);",
        "CREATE INDEX IF NOT EXISTS idx_audit_log_created_at ON auditlog (created_at DESC);",
        "CREATE INDEX IF NOT EXISTS idx_audit_log_action ON auditlog (action);",
        "CREATE INDEX IF NOT EXISTS idx_audit_log_entity_type ON auditlog (entity_type);",
        "CREATE INDEX IF NOT EXISTS idx_audit_log_user_id ON auditlog (user_id);",
    ]

    with engine.begin() as connection:
        for statement in statements:
            try:
                connection.exec_driver_sql(statement)
            except Exception as exc:
                logger.warning("Could not create index during init: %s", exc)
