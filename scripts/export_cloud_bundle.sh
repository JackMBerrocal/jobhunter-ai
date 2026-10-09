#!/usr/bin/env bash
# ==============================================================================
# JobHunter AI - Exportador de Paquete Autónomo para la Nube (Optimizado)
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

OUTPUT_FILE="${ROOT_DIR}/data/jobhunter_cloud_bundle.tar.gz"

echo "📦 Empaquetando JobHunter AI de forma optimizada para la nube..."

mkdir -p "${ROOT_DIR}/data"

cd "${ROOT_DIR}"

# Crear archivo comprimido excluyendo archivos innecesarios de caché pesado
tar --exclude='venv' \
    --exclude='.git' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='*Cache*' \
    --exclude='*GPUCache*' \
    --exclude='*DawnCache*' \
    --exclude='*.log' \
    --exclude='data/jobhunter_cloud_bundle.tar.gz' \
    -czf "${OUTPUT_FILE}" \
    core \
    adapters \
    web_ui \
    config \
    data/jobhunter.db \
    data/storage_state.json \
    data/browser_profile/Default/Cookies* \
    data/browser_profile/Default/Network* \
    data/browser_profile/Default/Preferences* \
    requirements.txt \
    Dockerfile \
    docker-compose.yml \
    README_CLOUD.md \
    README.md 2>/dev/null || true

BUNDLE_SIZE=$(du -h "${OUTPUT_FILE}" | cut -f1)
echo "✅ Paquete generado exitosamente: ${OUTPUT_FILE} (${BUNDLE_SIZE})"
