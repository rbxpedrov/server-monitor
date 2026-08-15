#!/data/data/com.termux/files/usr/bin/bash
# Mantém o Server Monitor rodando: se o processo cair por qualquer
# motivo (ex: o Android matou o app em background), reinicia sozinho.
# Uso recomendado: rodar dentro de uma sessão do termux-wake-lock,
# ou junto com o Termux:Boot pra iniciar sozinho quando o celular liga.
cd "$(dirname "$0")/.."

echo "Ativando wake-lock (evita o Android suspender o processo)..."
command -v termux-wake-lock >/dev/null 2>&1 && termux-wake-lock

while true; do
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Iniciando Server Monitor..."
    bash scripts/start.sh
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Server Monitor parou. Reiniciando em 5s..."
    sleep 5
done
