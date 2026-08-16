"""Armazenamento: espaço total/usado, além de tamanho aproximado das
pastas do Termux e do servidor Minecraft, quando identificáveis."""
import shutil
from pathlib import Path

from .utils import ok, unavailable
from . import config


def _dir_size_bytes(path: Path, max_seconds=2.0):
    """Soma o tamanho de um diretório com um limite de tempo, pra não
    travar o servidor em pastas gigantes (ex: mundo do Minecraft)."""
    import time
    start = time.time()
    total = 0
    try:
        for entry in path.rglob("*"):
            if time.time() - start > max_seconds:
                return total, True  # parcial (estourou o tempo)
            try:
                if entry.is_file():
                    total += entry.stat().st_size
            except (OSError, PermissionError):
                continue
    except (OSError, PermissionError):
        return None, False
    return total, False


def get_storage_info():
    try:
        usage = shutil.disk_usage(str(Path.home()))
    except OSError:
        return {
            "total_bytes": unavailable(),
            "used_bytes": unavailable(),
            "free_bytes": unavailable(),
            "percent_used": unavailable(),
            "status": unavailable(),
            "termux_size_bytes": unavailable(),
            "minecraft_size_bytes": unavailable(),
        }

    percent = round(usage.used / usage.total * 100, 1) if usage.total else 0
    if percent < 70:
        status = "normal"
    elif percent < 85:
        status = "atencao"
    else:
        status = "critico"

    termux_home = Path.home()
    termux_size, termux_partial = _dir_size_bytes(termux_home)

    mc_size = None
    mc_partial = False
    if config.MC_SERVER_DIR:
        mc_dir = Path(config.MC_SERVER_DIR)
        if mc_dir.exists():
            mc_size, mc_partial = _dir_size_bytes(mc_dir)

    return {
        "total_bytes": ok(usage.total),
        "used_bytes": ok(usage.used),
        "free_bytes": ok(usage.free),
        "percent_used": ok(percent),
        "status": ok(status),
        "termux_size_bytes": ok({"bytes": termux_size, "partial_estimate": termux_partial}) if termux_size is not None else unavailable(),
        "minecraft_size_bytes": ok({"bytes": mc_size, "partial_estimate": mc_partial}) if mc_size is not None else unavailable(),
    }
