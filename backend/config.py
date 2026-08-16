"""
Configuração central do Server Monitor.
Tudo o que for sensível (token de acesso, chave do GitHub, etc.)
vem de variáveis de ambiente / arquivo .env — nunca do frontend.
"""
import os
from pathlib import Path

# Tenta carregar um .env simples (sem depender de python-dotenv,
# pra evitar mais uma dependência em ambiente Termux).
def _load_dotenv(path: Path):
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


BASE_DIR = Path(__file__).resolve().parent.parent
_load_dotenv(BASE_DIR / ".env")

# --- Servidor ---
HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "8080"))

# --- Autenticação ---
# Defina um token forte no .env (AUTH_TOKEN=...). Sem ele, o servidor
# recusa iniciar em modo "produção" (ALLOW_NO_AUTH=false).
AUTH_TOKEN = os.environ.get("AUTH_TOKEN", "")
ALLOW_NO_AUTH = os.environ.get("ALLOW_NO_AUTH", "false").lower() == "true"

# --- Frontend / GitHub sync ---
FRONTEND_DIR = Path(os.environ.get("FRONTEND_DIR", str(BASE_DIR / "frontend")))
GIT_REPO_DIR = Path(os.environ.get("GIT_REPO_DIR", str(BASE_DIR)))
GIT_UPDATE_INTERVAL = int(os.environ.get("GIT_UPDATE_INTERVAL", "60"))

# --- Histórico ---
HISTORY_DB = Path(os.environ.get("HISTORY_DB", str(BASE_DIR / "backend" / "history.sqlite3")))
HISTORY_SAMPLE_INTERVAL = int(os.environ.get("HISTORY_SAMPLE_INTERVAL", "15"))  # segundos
HISTORY_RETENTION_HOURS = int(os.environ.get("HISTORY_RETENTION_HOURS", "24"))

# --- Minecraft ---
MC_HOST = os.environ.get("MC_HOST", "127.0.0.1")
MC_PORT = int(os.environ.get("MC_PORT", "25565"))
MC_SERVER_DIR = os.environ.get("MC_SERVER_DIR", "")  # pasta do servidor, se souber
MC_RCON_HOST = os.environ.get("MC_RCON_HOST", MC_HOST)
MC_RCON_PORT = int(os.environ.get("MC_RCON_PORT", "25575"))
MC_RCON_PASSWORD = os.environ.get("MC_RCON_PASSWORD", "")  # vazio = RCON desabilitado

# --- Alertas (limites configuráveis) ---
ALERT_CPU_PERCENT = float(os.environ.get("ALERT_CPU_PERCENT", "90"))
ALERT_RAM_PERCENT = float(os.environ.get("ALERT_RAM_PERCENT", "85"))
ALERT_STORAGE_PERCENT = float(os.environ.get("ALERT_STORAGE_PERCENT", "85"))
ALERT_BATTERY_LOW = float(os.environ.get("ALERT_BATTERY_LOW", "15"))
ALERT_TEMP_CELSIUS = float(os.environ.get("ALERT_TEMP_CELSIUS", "45"))

# --- Rede ---
PING_HOST = os.environ.get("PING_HOST", "8.8.8.8")
