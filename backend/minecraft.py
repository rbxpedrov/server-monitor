"""
Status do servidor Minecraft.

- Processo Java: via psutil (CPU/RAM/uptime do processo real).
- Online/jogadores/versão: via Server List Ping (protocolo nativo do
  Minecraft, sem dependências externas).
- TPS: só é possível via RCON (com um plugin/mod tipo Spark, ou
  comando nativo em servidores Paper/Spigot recentes). Se
  MC_RCON_PASSWORD não estiver configurado, fica indisponível — TPS
  não existe como métrica nativa do protocolo de status.
- Logs recentes: lidas do latest.log, se MC_SERVER_DIR apontar pra pasta certa.
"""
import json
import socket
import struct
import time
from pathlib import Path

import psutil

from .utils import ok, unavailable
from . import config

_start_time = {}  # pid -> primeira vez que vimos o processo, pra uptime


def _find_java_process():
    for p in psutil.process_iter(["pid", "name", "cmdline", "cpu_percent", "memory_percent", "create_time"]):
        try:
            info = p.info
            name = (info.get("name") or "").lower()
            cmdline = " ".join(info.get("cmdline") or []).lower()
            if "java" in name and ("server.jar" in cmdline or "minecraft" in cmdline or "spigot" in cmdline or "paper" in cmdline or "fabric" in cmdline):
                return info
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return None


def _write_varint(value: int) -> bytes:
    out = b""
    while True:
        byte = value & 0x7F
        value >>= 7
        if value:
            out += bytes([byte | 0x80])
        else:
            out += bytes([byte])
            return out


def _read_varint(sock) -> int:
    value = 0
    for i in range(10):
        byte = sock.recv(1)
        if not byte:
            raise ConnectionError("conexão fechada durante leitura do varint")
        b = byte[0]
        value |= (b & 0x7F) << (7 * i)
        if not (b & 0x80):
            return value
    raise ValueError("varint muito longo")


def _slp_status(host: str, port: int, timeout=2.5):
    """Server List Ping — funciona em qualquer servidor 1.7+."""
    with socket.create_connection((host, port), timeout=timeout) as sock:
        host_bytes = host.encode("utf-8")
        handshake = (
            _write_varint(0x00)
            + _write_varint(-1)  # protocol version (any)
            + _write_varint(len(host_bytes)) + host_bytes
            + struct.pack(">H", port)
            + _write_varint(1)  # next state: status
        )
        packet = _write_varint(len(handshake)) + handshake
        sock.sendall(packet)
        sock.sendall(_write_varint(1) + _write_varint(0x00))  # status request

        _read_varint(sock)  # tamanho total do pacote de resposta
        packet_id = _read_varint(sock)
        if packet_id != 0x00:
            raise ValueError("resposta inesperada do servidor")
        length = _read_varint(sock)
        data = b""
        while len(data) < length:
            chunk = sock.recv(length - len(data))
            if not chunk:
                break
            data += chunk
        return json.loads(data.decode("utf-8"))


def _ping_latency(host: str, port: int, timeout=2.5):
    start = time.time()
    try:
        with socket.create_connection((host, port), timeout=timeout):
            pass
        return round((time.time() - start) * 1000, 1)
    except OSError:
        return None


def _read_recent_logs(lines=20):
    if not config.MC_SERVER_DIR:
        return unavailable()
    log_path = Path(config.MC_SERVER_DIR) / "logs" / "latest.log"
    if not log_path.exists():
        return unavailable()
    try:
        content = log_path.read_text(encoding="utf-8", errors="ignore").splitlines()
        return ok(content[-lines:])
    except (OSError, PermissionError):
        return unavailable()


def get_minecraft_info():
    proc_info = _find_java_process()
    process_data = unavailable()
    if proc_info:
        pid = proc_info["pid"]
        _start_time.setdefault(pid, proc_info.get("create_time"))
        uptime_s = time.time() - (proc_info.get("create_time") or time.time())
        process_data = ok({
            "pid": pid,
            "cpu_percent": round(proc_info.get("cpu_percent") or 0, 1),
            "ram_percent": round(proc_info.get("memory_percent") or 0, 1),
            "uptime_seconds": int(uptime_s),
        })

    status_data = unavailable()
    players_online = unavailable()
    players_max = unavailable()
    player_list = unavailable()
    version = unavailable()
    motd = unavailable()

    try:
        status = _slp_status(config.MC_HOST, config.MC_PORT)
        version = ok(status.get("version", {}).get("name"))
        players = status.get("players", {})
        players_online = ok(players.get("online"))
        players_max = ok(players.get("max"))
        sample = players.get("sample")
        player_list = ok([p.get("name") for p in sample]) if sample else unavailable()
        raw_motd = status.get("description")
        if isinstance(raw_motd, dict):
            raw_motd = raw_motd.get("text", "")
        motd = ok(raw_motd) if raw_motd else unavailable()
        status_data = ok(True)
    except (OSError, ConnectionError, ValueError, socket.timeout):
        status_data = ok(False)

    ping_ms = _ping_latency(config.MC_HOST, config.MC_PORT)

    # TPS só via RCON configurado + comando de plugin (ex: Paper 'tps')
    tps = unavailable()
    if config.MC_RCON_PASSWORD:
        tps = _try_rcon_tps()

    return {
        "online": status_data,
        "address": ok(config.MC_HOST),
        "port": ok(config.MC_PORT),
        "version": version,
        "motd": motd,
        "players_online": players_online,
        "players_max": players_max,
        "player_list": player_list,
        "ping_ms": ok(ping_ms) if ping_ms is not None else unavailable(),
        "process": process_data,
        "tps": tps,
        "recent_logs": _read_recent_logs(),
    }


def _try_rcon_tps():
    """Implementação mínima do protocolo RCON só pro comando 'tps'.
    Requer rcon habilitado no server.properties e MC_RCON_PASSWORD no .env."""
    try:
        with socket.create_connection((config.MC_RCON_HOST, config.MC_RCON_PORT), timeout=2) as sock:
            def send_packet(pkt_id, pkt_type, payload):
                body = struct.pack("<ii", pkt_id, pkt_type) + payload.encode("utf-8") + b"\x00\x00"
                sock.sendall(struct.pack("<i", len(body)) + body)

            def read_packet():
                length = struct.unpack("<i", sock.recv(4))[0]
                data = sock.recv(length)
                return data[8:-2].decode("utf-8", errors="ignore")

            send_packet(1, 3, config.MC_RCON_PASSWORD)  # SERVERDATA_AUTH
            read_packet()
            send_packet(2, 2, "tps")  # SERVERDATA_EXECCOMMAND
            reply = read_packet()
            return ok(reply.strip())
    except (OSError, struct.error):
        return unavailable()
