#!/data/data/com.termux/files/usr/bin/bash
# Inicia o Server Monitor no Termux.
set -e

cd "$(dirname "$0")/.."

if [ ! -d "venv" ]; then
    echo "Ambiente virtual não encontrado. Rode primeiro: bash scripts/install.sh (veja o README)"
    exit 1
fi

source venv/bin/activate

if [ ! -f ".env" ]; then
    echo "Arquivo .env não encontrado. Copie .env.example para .env e configure o AUTH_TOKEN."
    exit 1
fi

echo "Iniciando Server Monitor em http://0.0.0.0:${PORT:-8080} ..."
exec uvicorn backend.server:app --host "${HOST:-0.0.0.0}" --port "${PORT:-8080}"
