# Sistema de Arquivo Morto Digital
## Câmaras Municipais - Gestão Documental

Sistema completo de digitalização e gestão de documentos com OCR em Português.

## Tecnologias

- **Backend**: Python 3.12 + FastAPI
- **Banco de Dados**: PostgreSQL 16
- **OCR**: Tesseract (Português)
- **Frontend**: HTML5 + Tailwind CSS + JavaScript
- **Containerização**: Docker + Docker Compose

## Funcionalidades

- Digitalização automática com OCR (PDF, JPG, PNG)
- Busca inteligente em milissegundos
- Sistema RBAC com 3 níveis: Administrador, Operador, Consulta
- Auditoria completa (LGPD)
- Autenticação JWT
- Armazenamento organizado por Ano/Mês/Setor

## Instalação (Ubuntu 24.04 LTS)

### Pré-requisitos
```bash
sudo apt update
sudo apt install docker.io docker-compose git
sudo systemctl enable docker
sudo systemctl start docker
```

### Deploy

1. Clone o projeto:
```bash
git clone <seu-repositorio>
cd Camaradoc
```

2. Inicie o sistema:
```bash
sudo docker-compose up --build -d
```

3. Acesse o sistema:
```
Frontend: http://localhost
API: http://localhost:8000
Documentação API: http://localhost:8000/docs
```

### Credenciais Padrão

**Usuário**: admin@camara.gov.br  
**Senha**: admin123

⚠️ **IMPORTANTE**: Altere essas credenciais após o primeiro acesso!

## Estrutura de Pastas

```
Camaradoc/
├── backend/
│   ├── app/
│   │   ├── models.py          # Modelos de banco de dados
│   │   ├── main.py            # API FastAPI
│   │   └── ocr_engine.py      # Motor OCR
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   └── index.html             # Dashboard
├── uploads/                   # Documentos (gerado automaticamente)
├── docker-compose.yml
└── nginx.conf
```

## Uso

### Upload de Documentos

1. Faça login com usuário Operador ou Administrador
2. Preencha título, setor e descrição
3. Selecione o arquivo (PDF/JPG/PNG)
4. O OCR será processado automaticamente

### Busca

Digite qualquer termo na barra de busca. O sistema procura em:
- Títulos
- Descrições
- Conteúdo extraído pelo OCR

### Logs de Auditoria

Disponível apenas para Administradores. Registra:
- Login/Logout
- Uploads
- Buscas
- Visualizações
- Downloads

## Conformidade LGPD

O sistema registra obrigatoriamente:
- Quem acessou cada documento
- Data e hora do acesso
- IP de origem
- Tipo de ação realizada

## Backup

### Banco de Dados
```bash
docker exec arquivo_morto_db pg_dump -U arquivo_user arquivo_morto > backup.sql
```

### Arquivos
```bash
sudo tar -czf uploads_backup.tar.gz uploads/
```

## Suporte

Sistema desenvolvido para Câmaras Municipais.
Conformidade com LGPD e requisitos de órgãos públicos.
