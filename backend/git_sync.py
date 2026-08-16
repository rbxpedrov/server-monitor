"""
Sincronização com o GitHub — roda em background dentro do próprio
processo (asyncio task), sem travar a API. Só atualiza os arquivos do
FRONTEND (HTML/CSS/JS/assets). Nenhum dado de sensor é enviado ao GitHub.
"""
import asyncio
import subprocess
import time

from . import config
from . import history

_last_sync = {"time": None, "status": "nunca executado", "commit": None}


def _run_git(args, cwd):
    try:
        result = subprocess.run(
            ["git"] + args, cwd=str(cwd), capture_output=True, text=True, timeout=30
        )
        return result.returncode == 0, (result.stdout + result.stderr).strip()
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        return False, str(e)


def get_sync_status():
    return dict(_last_sync)


async def sync_once():
    """Roda o git em uma thread separada (asyncio.to_thread) pra não
    bloquear o event loop / a API enquanto o fetch+pull acontece."""
    repo = config.GIT_REPO_DIR
    if not (repo / ".git").exists():
        _last_sync.update(time=time.time(), status="repositório git não encontrado", commit=None)
        return

    ok_fetch, out_fetch = await asyncio.to_thread(_run_git, ["fetch", "--quiet"], repo)
    if not ok_fetch:
        _last_sync.update(time=time.time(), status=f"erro no fetch: {out_fetch}", commit=None)
        history.add_event("error", f"Falha ao sincronizar GitHub: {out_fetch[:200]}")
        return

    ok_pull, out_pull = await asyncio.to_thread(_run_git, ["pull", "--quiet"], repo)
    ok_rev, commit = await asyncio.to_thread(_run_git, ["rev-parse", "--short", "HEAD"], repo)

    if ok_pull:
        _last_sync.update(time=time.time(), status="atualizado", commit=commit if ok_rev else None)
        if "Already up to date" not in out_pull and out_pull:
            history.add_event("info", "Frontend atualizado a partir do GitHub")
    else:
        _last_sync.update(time=time.time(), status=f"erro no pull: {out_pull}", commit=None)
        history.add_event("error", f"Falha no git pull: {out_pull[:200]}")


async def git_sync_loop():
    """Task de background: verifica o GitHub a cada GIT_UPDATE_INTERVAL segundos."""
    while True:
        try:
            await sync_once()
        except Exception as e:
            history.add_event("error", f"Erro inesperado na sincronização GitHub: {e}")
        await asyncio.sleep(config.GIT_UPDATE_INTERVAL)
