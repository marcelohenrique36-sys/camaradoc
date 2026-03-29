#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="${PROJECT_DIR:-/home/marcelo/camaradoc}"
BRANCH="${BRANCH:-main}"
HEALTH_URL="${HEALTH_URL:-http://127.0.0.1/health}"
HEALTH_TIMEOUT_SECONDS="${HEALTH_TIMEOUT_SECONDS:-120}"

echo "[1/5] Entrando em ${PROJECT_DIR}"
cd "${PROJECT_DIR}"

echo "[2/5] Atualizando codigo (${BRANCH})"
git fetch origin "${BRANCH}"
git checkout "${BRANCH}"
git pull --ff-only origin "${BRANCH}"

echo "[3/5] Subindo stack com rebuild"
docker compose up -d --build

echo "[4/5] Aguardando health check em ${HEALTH_URL}"
elapsed=0
until curl -fsS "${HEALTH_URL}" >/dev/null; do
  sleep 2
  elapsed=$((elapsed + 2))
  if [ "${elapsed}" -ge "${HEALTH_TIMEOUT_SECONDS}" ]; then
    echo "Health check nao ficou pronto em ${HEALTH_TIMEOUT_SECONDS}s"
    docker compose logs --tail=120 api
    docker compose logs --tail=120 worker
    exit 1
  fi
done

echo "[5/5] Stack pronta"
docker compose ps
echo "API health: $(curl -fsS "${HEALTH_URL}")"
echo
echo "Logs recentes API:"
docker compose logs --tail=50 api
echo
echo "Logs recentes Worker:"
docker compose logs --tail=50 worker
