"""Helpers compartilhados entre os módulos de coleta."""
import subprocess


def unavailable():
    return {"available": False, "value": None}


def ok(value):
    return {"available": True, "value": value}


def run_cmd(args, timeout=3):
    """Executa um comando externo e devolve stdout (str) ou None se falhar.
    Usado pros comandos termux-api, ping, etc. Nunca lança exceção pra fora —
    se o comando não existir ou falhar, apenas retornamos None (indisponível)."""
    try:
        result = subprocess.run(
            args, capture_output=True, text=True, timeout=timeout
        )
        if result.returncode != 0:
            return None
        return result.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return None
