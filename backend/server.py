"""
Server Monitor — API + dashboard para monitorar o celular servidor
(Android/Termux) que hospeda o servidor de Minecraft.

Rodar com: uvicorn backend.server:app --host 0.0.0.0 --port 8080
(o scripts/start.sh já faz isso)
"""
import asyncio
import time

from fastapi import Depends, FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import alerts, battery, config, git_sync, history, minecraft
from . import network as net_mod
from . import processes, storage, system, temperature
from .auth import require_auth, require_auth_ws

app = FastAPI(title="Server Monitor")

_start_ts = time.time()


# ---------------------------------------------------------------------
# Snapshot central: coleta tudo de uma vez só, reaproveitado por todas
# as rotas + pelo WebSocket + pelo sampler de histórico. Evita ficar
# lendo /proc e /sys repetidamente à toa.
# ---------------------------------------------------------------------
def build_snapshot():
    cpu = system.get_cpu_info()
    ram = system.get_ram_info()
    stor = storage.get_storage_info()
    batt = battery.get_battery_info()
    temp = temperature.get_temperature_info()
    net = net_mod.get_network_info()
    mc = minecraft.get_minecraft_info()
    android = system.get_android_info()

    active_alerts = alerts.compute_alerts(cpu, ram, stor, batt, temp, net, mc)

    return {
        "timestamp": time.time(),
        "cpu": cpu,
        "ram": ram,
        "storage": stor,
        "battery": batt,
        "temperature": temp,
        "network": net,
        "minecraft": mc,
        "android": android,
        "alerts": active_alerts,
        "git_sync": git_sync.get_sync_status(),
    }


# --- Rotas da API (todas exigem autenticação) ---------------------------

@app.get("/api/status")
def api_status(_=Depends(require_auth)):
    return build_snapshot()


@app.get("/api/system")
def api_system(_=Depends(require_auth)):
    return system.get_android_info()


@app.get("/api/cpu")
def api_cpu(_=Depends(require_auth)):
    return system.get_cpu_info()


@app.get("/api/memory")
def api_memory(_=Depends(require_auth)):
    return system.get_ram_info()


@app.get("/api/storage")
def api_storage(_=Depends(require_auth)):
    return storage.get_storage_info()


@app.get("/api/battery")
def api_battery(_=Depends(require_auth)):
    return battery.get_battery_info()


@app.get("/api/temperature")
def api_temperature(_=Depends(require_auth)):
    return temperature.get_temperature_info()


@app.get("/api/network")
def api_network(_=Depends(require_auth)):
    return net_mod.get_network_info()


@app.get("/api/processes")
def api_processes(sort: str = "cpu", limit: int = 30, _=Depends(require_auth)):
    return processes.get_processes(sort_by=sort, limit=limit)


@app.get("/api/minecraft")
def api_minecraft(_=Depends(require_auth)):
    return minecraft.get_minecraft_info()


@app.get("/api/history")
def api_history(period: str = "1h", _=Depends(require_auth)):
    return {"period": period, "series": history.get_series(period)}


@app.get("/api/events")
def api_events(limit: int = 50, _=Depends(require_auth)):
    return {"events": history.get_events(limit)}


@app.get("/api/git-sync")
def api_git_sync(_=Depends(require_auth)):
    return git_sync.get_sync_status()


# --- WebSocket para atualização em tempo real ----------------------------

@app.websocket("/ws")
async def ws_status(websocket: WebSocket):
    if not await require_auth_ws(websocket):
        return
    await websocket.accept()
    try:
        while True:
            await websocket.send_json(build_snapshot())
            await asyncio.sleep(3)
    except WebSocketDisconnect:
        pass


# --- Tarefas em background -----------------------------------------------

async def _history_sampler_loop():
    while True:
        try:
            snap = build_snapshot()
            history.insert_sample(
                cpu=snap["cpu"]["usage_total_percent"].get("value"),
                ram=snap["ram"]["percent_used"].get("value"),
                battery=snap["battery"]["percentage"].get("value"),
                temp=snap["temperature"]["battery_celsius"].get("value"),
                ping=snap["network"]["ping_ms"].get("value"),
                storage=snap["storage"]["percent_used"].get("value"),
                players=snap["minecraft"]["players_online"].get("value"),
            )
        except Exception as e:
            history.add_event("error", f"Erro ao coletar amostra de histórico: {e}")
        await asyncio.sleep(config.HISTORY_SAMPLE_INTERVAL)


async def _history_cleanup_loop():
    while True:
        await asyncio.sleep(3600)
        history.cleanup_old()


@app.on_event("startup")
async def on_startup():
    history.init_db()
    asyncio.create_task(_history_sampler_loop())
    asyncio.create_task(_history_cleanup_loop())
    asyncio.create_task(git_sync.git_sync_loop())


# --- Frontend estático (servido por último, pra não conflitar com /api) --

app.mount("/assets", StaticFiles(directory=str(config.FRONTEND_DIR / "assets")), name="assets")


@app.get("/")
def index():
    return FileResponse(str(config.FRONTEND_DIR / "index.html"))


@app.get("/style.css")
def style_css():
    return FileResponse(str(config.FRONTEND_DIR / "style.css"))


@app.get("/script.js")
def script_js():
    return FileResponse(str(config.FRONTEND_DIR / "script.js"))
