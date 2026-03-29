#!/usr/bin/env bash
set -euo pipefail

if ! command -v jq >/dev/null 2>&1; then
  echo "Dependencia ausente: jq"
  echo "Instale com: sudo apt-get update && sudo apt-get install -y jq"
  exit 1
fi

if [ "${1:-}" = "" ]; then
  echo "Uso: $0 /caminho/arquivo.pdf"
  exit 1
fi

PDF_PATH="$1"
if [ ! -f "${PDF_PATH}" ]; then
  echo "Arquivo nao encontrado: ${PDF_PATH}"
  exit 1
fi

BASE_URL="${BASE_URL:-http://127.0.0.1}"
ADMIN_EMAIL="${ADMIN_EMAIL:-admin@camaradoc.local}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-123456}"
OCR_WAIT_SECONDS="${OCR_WAIT_SECONDS:-180}"

echo "[1/8] Login admin"
TOKEN="$(
  curl -fsS -X POST "${BASE_URL}/auth/login" \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"${ADMIN_EMAIL}\",\"password\":\"${ADMIN_PASSWORD}\"}" \
  | jq -r ".access_token"
)"

if [ -z "${TOKEN}" ] || [ "${TOKEN}" = "null" ]; then
  echo "Falha ao obter token"
  exit 1
fi

TS="$(date +%s)"
SECTOR_NAME="Setor Script ${TS}"
TYPE_NAME="Tipo Script ${TS}"

echo "[2/8] Criando setor"
SECTOR_JSON="$(
  curl -fsS -X POST "${BASE_URL}/sectors" \
    -H "Authorization: Bearer ${TOKEN}" \
    -H "Content-Type: application/json" \
    -d "{\"name\":\"${SECTOR_NAME}\",\"description\":\"Criado por smoke_test\"}"
)"
SECTOR_ID="$(echo "${SECTOR_JSON}" | jq -r ".id")"

echo "[3/8] Criando tipo de documento"
TYPE_JSON="$(
  curl -fsS -X POST "${BASE_URL}/document-types" \
    -H "Authorization: Bearer ${TOKEN}" \
    -H "Content-Type: application/json" \
    -d "{\"name\":\"${TYPE_NAME}\",\"description\":\"Criado por smoke_test\"}"
)"
TYPE_ID="$(echo "${TYPE_JSON}" | jq -r ".id")"

echo "[4/8] Upload de documento"
DOC_JSON="$(
  curl -fsS -X POST "${BASE_URL}/documents/upload" \
    -H "Authorization: Bearer ${TOKEN}" \
    -F "title=Documento Script ${TS}" \
    -F "document_type_id=${TYPE_ID}" \
    -F "sector_id=${SECTOR_ID}" \
    -F "number=${TS}" \
    -F "year=$(date +%Y)" \
    -F "subject=Teste automatizado" \
    -F "author_origin=Script Ubuntu" \
    -F "access_level=interno" \
    -F "file=@${PDF_PATH};type=application/pdf"
)"
DOC_ID="$(echo "${DOC_JSON}" | jq -r ".id")"

echo "[5/8] Aguardando OCR (timeout ${OCR_WAIT_SECONDS}s)"
elapsed=0
OCR_STATUS="pending"
while true; do
  DOC_STATUS_JSON="$(
    curl -fsS "${BASE_URL}/documents/${DOC_ID}" \
      -H "Authorization: Bearer ${TOKEN}"
  )"
  OCR_STATUS="$(echo "${DOC_STATUS_JSON}" | jq -r ".ocr_status")"
  if [ "${OCR_STATUS}" = "done" ] || [ "${OCR_STATUS}" = "error" ]; then
    break
  fi
  sleep 3
  elapsed=$((elapsed + 3))
  if [ "${elapsed}" -ge "${OCR_WAIT_SECONDS}" ]; then
    echo "Timeout aguardando OCR"
    break
  fi
done

echo "[6/8] Resultado OCR: ${OCR_STATUS}"
if [ "${OCR_STATUS}" = "error" ]; then
  echo "Detalhe: $(echo "${DOC_STATUS_JSON}" | jq -r ".ocr_error")"
fi

echo "[7/8] Testando busca textual"
SEARCH_JSON="$(
  curl -fsS "${BASE_URL}/documents/search?q=Teste%20automatizado" \
    -H "Authorization: Bearer ${TOKEN}"
)"
SEARCH_COUNT="$(echo "${SEARCH_JSON}" | jq "length")"
echo "Resultados da busca: ${SEARCH_COUNT}"

echo "[8/8] Testando download"
curl -fsS -o "/tmp/camaradoc_${DOC_ID}.pdf" \
  "${BASE_URL}/documents/${DOC_ID}/download" \
  -H "Authorization: Bearer ${TOKEN}"
echo "Arquivo baixado em /tmp/camaradoc_${DOC_ID}.pdf"

echo
echo "Smoke test concluido."
