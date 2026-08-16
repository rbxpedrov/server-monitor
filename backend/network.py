"""
Rede — Wi-Fi (via termux-wifi-connectioninfo), IP local, contadores de
tráfego (via psutil) e latência (via ping do sistema).

Sobre 'velocidade de download/upload': não fazemos um speedtest real
(consumiria dados móveis e CPU à toa num celular que já está rodando o
Minecraft). Em vez disso calculamos a TAXA de tráfego real da interface
(bytes/s) entre duas leituras — isso é rotulado como "taxa atual", não
como resultado de teste de velocidade.
"""
import json
import socket
import time

import psutil

from .utils import ok, unavailable, run_cmd
from . import config

_last_io = {"time": None, "sent": None, "recv": None}


def _get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.5)
        s.connect((config.PING_HOST, 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except OSError:
        return None


def _get_wifi_info():
    raw = run_cmd(["termux-wifi-connectioninfo"], timeout=3)
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def _ping(host: str):
    out = run_cmd(["ping", "-c", "1", "-w", "2", host], timeout=4)
    if out is None:
        return None
    for line in out.splitlines():
        if "time=" in line:
            try:
                return float(line.split("time=")[1].split()[0])
            except (ValueError, IndexError):
                return None
    return None


def _traffic_rate():
    global _last_io
    counters = psutil.net_io_counters()
    now = time.time()
    prev = _last_io
    _last_io = {"time": now, "sent": counters.bytes_sent, "recv": counters.bytes_recv}

    if prev["time"] is None:
        return None, None, counters.bytes_sent, counters.bytes_recv, counters.errin + counters.errout, counters.dropin + counters.dropout

    elapsed = max(now - prev["time"], 0.001)
    up_bps = (counters.bytes_sent - prev["sent"]) / elapsed
    down_bps = (counters.bytes_recv - prev["recv"]) / elapsed
    return down_bps, up_bps, counters.bytes_sent, counters.bytes_recv, counters.errin + counters.errout, counters.dropin + counters.dropout


def get_network_info():
    wifi = _get_wifi_info()
    local_ip = _get_local_ip()
    ping_ms = _ping(config.PING_HOST)
    down_bps, up_bps, sent, recv, errors, drops = _traffic_rate()

    connected = wifi is not None and wifi.get("supplicant_state") == "COMPLETED" if wifi else None

    data = {
        "wifi_connected": ok(connected) if connected is not None else unavailable(),
        "ssid": ok(wifi.get("ssid")) if wifi and wifi.get("ssid") not in (None, "<unknown ssid>") else unavailable(),
        "local_ip": ok(local_ip) if local_ip else unavailable(),
        "gateway": unavailable(),  # Android normalmente não expõe isso sem root
        "dns": unavailable(),
        "connection_type": ok("wifi") if wifi else unavailable(),
        "download_rate_bps": ok(round(down_bps, 1)) if down_bps is not None else unavailable(),
        "upload_rate_bps": ok(round(up_bps, 1)) if up_bps is not None else unavailable(),
        "bytes_received": ok(recv),
        "bytes_sent": ok(sent),
        "network_errors": ok(errors),
        "packet_drops": ok(drops),
        "ping_ms": ok(ping_ms) if ping_ms is not None else unavailable(),
        "internet_online": ok(ping_ms is not None),
    }
    return data
