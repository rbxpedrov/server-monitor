#!/data/data/com.termux/files/usr/bin/bash
# Força uma sincronização manual com o GitHub (o servidor já faz isso
# sozinho em background, esse script é só pra quando você quiser
# forçar uma atualização imediata sem esperar o intervalo).
set -e
cd "$(dirname "$0")/.."
git fetch --quiet
git pull --quiet
echo "Frontend atualizado. Commit atual: $(git rev-parse --short HEAD)"
