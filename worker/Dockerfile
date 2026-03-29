# Usamos a imagem oficial e leve do Python
FROM python:3.11-slim

# Variáveis para o Python não criar arquivos .pyc e cuspir os logs em tempo real
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Instala as dependências reais de sistema para o OCRmyPDF e para o PostgreSQL
RUN apt-get update && apt-get install -y \
    ocrmypdf \
    tesseract-ocr-por \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Define a pasta de trabalho dentro do container
WORKDIR /app

# Copia as dependências e instala
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia o nosso código
COPY worker.py .

# Roda o worker
CMD ["python", "worker.py"]