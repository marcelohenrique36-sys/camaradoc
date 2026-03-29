"""
Motor OCR - Extração de Texto de Documentos
Suporte: PDF, JPG, PNG com Tesseract OCR em Português
"""

import os
import pytesseract
from PIL import Image
from pdf2image import convert_from_path
import logging
from typing import Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class OCREngine:
    """Classe responsável pela extração de texto de documentos"""
    
    def __init__(self, tesseract_path: str = "/usr/bin/tesseract"):
        """
        Inicializa o motor OCR
        
        Args:
            tesseract_path: Caminho do executável Tesseract (padrão Linux)
        """
        pytesseract.pytesseract.tesseract_cmd = tesseract_path
        self.idioma = "por"
        
    def extrair_texto_imagem(self, caminho_imagem: str) -> Optional[str]:
        """
        Extrai texto de arquivo de imagem (JPG, PNG)
        
        Args:
            caminho_imagem: Caminho completo do arquivo de imagem
            
        Returns:
            Texto extraído ou None em caso de erro
        """
        try:
            logger.info(f"Processando imagem: {caminho_imagem}")
            imagem = Image.open(caminho_imagem)
            
            texto = pytesseract.image_to_string(imagem, lang=self.idioma)
            
            logger.info(f"Texto extraído com sucesso. Tamanho: {len(texto)} caracteres")
            return texto.strip()
            
        except Exception as e:
            logger.error(f"Erro ao processar imagem {caminho_imagem}: {str(e)}")
            return None
    
    def extrair_texto_pdf(self, caminho_pdf: str) -> Optional[str]:
        """
        Extrai texto de arquivo PDF usando conversão para imagem + OCR
        
        Args:
            caminho_pdf: Caminho completo do arquivo PDF
            
        Returns:
            Texto extraído de todas as páginas ou None em caso de erro
        """
        try:
            logger.info(f"Processando PDF: {caminho_pdf}")
            
            paginas = convert_from_path(caminho_pdf, dpi=300)
            
            texto_completo = []
            
            for i, pagina in enumerate(paginas, start=1):
                logger.info(f"Processando página {i}/{len(paginas)}")
                texto_pagina = pytesseract.image_to_string(pagina, lang=self.idioma)
                texto_completo.append(texto_pagina)
            
            texto_final = "\n\n".join(texto_completo).strip()
            logger.info(f"PDF processado com sucesso. Total: {len(texto_final)} caracteres")
            
            return texto_final
            
        except Exception as e:
            logger.error(f"Erro ao processar PDF {caminho_pdf}: {str(e)}")
            return None
    
    def processar_documento(self, caminho_arquivo: str) -> Optional[str]:
        """
        Processa automaticamente PDF ou Imagem baseado na extensão
        
        Args:
            caminho_arquivo: Caminho completo do arquivo
            
        Returns:
            Texto extraído ou None em caso de erro
        """
        if not os.path.exists(caminho_arquivo):
            logger.error(f"Arquivo não encontrado: {caminho_arquivo}")
            return None
        
        extensao = os.path.splitext(caminho_arquivo)[1].lower()
        
        if extensao == ".pdf":
            return self.extrair_texto_pdf(caminho_arquivo)
        elif extensao in [".jpg", ".jpeg", ".png"]:
            return self.extrair_texto_imagem(caminho_arquivo)
        else:
            logger.error(f"Formato não suportado: {extensao}")
            return None
