import os
import time
import logging
import psycopg2
import ocrmypdf
from psycopg2.extras import RealDictCursor

# Configuração de Logs
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("OCR_Worker")

# Pegando a URL do banco pelas variáveis de ambiente (ajuste o default se necessário)
DB_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@db:5432/camaradoc")

def get_db_connection():
    return psycopg2.connect(DB_URL)

def process_pending_documents():
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Busca 1 documento pendente e trava a linha para evitar concorrência (SKIP LOCKED)
        cur.execute("""
            SELECT id, original_file_path 
            FROM document 
            WHERE ocr_status = 'pending' 
            LIMIT 1 
            FOR UPDATE SKIP LOCKED;
        """)
        doc = cur.fetchone()
        
        if not doc:
            cur.close()
            conn.close()
            return # Nenhum documento pendente
            
        doc_id = doc['id']
        original_path = doc['original_file_path']
        
        # 1. Atualiza o status para "processing"
        cur.execute("UPDATE document SET ocr_status = 'processing' WHERE id = %s;", (doc_id,))
        conn.commit()
        logger.info(f"Iniciando processamento do documento ID: {doc_id}")
        
        # 2. Prepara os caminhos
        filename = os.path.basename(original_path)
        ocr_path = f"/storage/ocr/{filename}"
        txt_path = f"/storage/temp/{filename}.txt"
        
        try:
            # 3. Executa o OCR
            ocrmypdf.ocr(
                input_file=original_path,
                output_file=ocr_path,
                language="por",
                skip_text=True,       # Pula páginas que já têm texto digital
                sidecar=txt_path,     # Extrai todo o texto para este arquivo .txt
                force_ocr=False
            )
            
            # 4. Lê o texto extraído
            extracted_text = ""
            if os.path.exists(txt_path):
                with open(txt_path, 'r', encoding='utf-8') as f:
                    extracted_text = f.read()
                # Limpa o arquivo temporário
                os.remove(txt_path)
            
            # 5. Atualiza o banco com sucesso
            cur.execute("""
                UPDATE document 
                SET ocr_status = 'success', 
                    ocr_file_path = %s, 
                    extracted_text = %s 
                WHERE id = %s;
            """, (ocr_path, extracted_text, doc_id))
            conn.commit()
            logger.info(f"Documento ID: {doc_id} processado com sucesso!")

        except Exception as e:
            logger.error(f"Erro no OCR do documento ID {doc_id}: {str(e)}")
            # Em caso de falha no OCR, atualiza o status para error
            cur.execute("UPDATE document SET ocr_status = 'error' WHERE id = %s;", (doc_id,))
            conn.commit()

        finally:
            cur.close()

    except Exception as db_err:
        logger.error(f"Erro de conexão com o banco de dados: {str(db_err)}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    logger.info("Worker de OCR iniciado. Aguardando documentos...")
    # Loop infinito rodando a cada 5 segundos
    while True:
        process_pending_documents()
        time.sleep(5)