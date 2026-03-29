#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="${PROJECT_DIR:-/home/marcelo/camaradoc}"
BACKUP_DIR="${BACKUP_DIR:-/home/marcelo/backups/camaradoc}"
TS="$(date +%Y%m%d_%H%M%S)"

if [ -f "${PROJECT_DIR}/.env" ]; then
  # shellcheck disable=SC1090
  source "${PROJECT_DIR}/.env"
fi

echo "[1/4] Preparando diretorio de backup"
mkdir -p "${BACKUP_DIR}/${TS}"
cd "${PROJECT_DIR}"

echo "[2/4] Exportando banco PostgreSQL"
DB_CONTAINER="${DB_CONTAINER:-camaradoc_db}"
POSTGRES_USER="${POSTGRES_USER:-postgres}"
POSTGRES_DB="${POSTGRES_DB:-postgres}"

docker exec "${DB_CONTAINER}" pg_dump -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" \
  > "${BACKUP_DIR}/${TS}/database.sql"

echo "[3/4] Compactando storage"
tar -czf "${BACKUP_DIR}/${TS}/storage.tar.gz" -C "${PROJECT_DIR}" storage

echo "[4/4] Backup finalizado"
ls -lh "${BACKUP_DIR}/${TS}"
