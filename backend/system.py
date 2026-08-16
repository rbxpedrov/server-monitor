"""
CPU, RAM e informações gerais do Android — tudo via psutil + /proc + /sys.
Nada aqui é inventado: o que o Android/Termux não expõe vem marcado
como indisponível.
"""
import os
import platform
import time
from pathlib import Path

import psutil

from .utils import ok, unavailable, run_cmd

_BOOT_TIME = psutil.boot_time()


def _read_int(path: str):
    try:
        return int(Path(path).read_text().strip())
    except (FileNotFoundError, ValueError, PermissionError):
        return None


def get_cpu_freqs():
    """Frequência atual/min/max lida de /sys — psutil.cpu_freq() costuma
    falhar em muitos kernels Android, então lemos direto por núcleo."""
    cur, mn, mx = [], [], []
    n = psutil.cpu_count(logical=True) or 0
    for i in range(n):
        base = f"/sys/devices/system/cpu/cpu{i}/cpufreq"
        c = _read_int(f"{base}/scaling_cur_freq")
        lo = _read_int(f"{base}/cpuinfo_min_freq")
        hi = _read_int(f"{base}/cpuinfo_max_freq")
        if c is not None:
            cur.append(c / 1000)  # kHz -> MHz
        if lo is not None:
            mn.append(lo / 1000)
        if hi is not None:
            mx.append(hi / 1000)
    return cur, mn, mx


def get_cpu_info():
    try:
        percent_total = psutil.cpu_percent(interval=0.3)
        percent_per_core = psutil.cpu_percent(interval=0.0, percpu=True)
    except Exception:
        percent_total, percent_per_core = None, []

    cur, mn, mx = get_cpu_freqs()

    try:
        load1, load5, load15 = os.getloadavg()
        load_avg = ok({"1min": round(load1, 2), "5min": round(load5, 2), "15min": round(load15, 2)})
    except (OSError, AttributeError):
        load_avg = unavailable()

    arch = platform.machine() or None

    model = None
    try:
        cpuinfo = Path("/proc/cpuinfo").read_text()
        for line in cpuinfo.splitlines():
            if line.lower().startswith(("model name", "hardware", "processor")):
                model = line.split(":", 1)[1].strip()
                break
    except (FileNotFoundError, PermissionError):
        pass

    top_process = _top_process_by("cpu")

    return {
        "usage_total_percent": ok(percent_total) if percent_total is not None else unavailable(),
        "usage_per_core_percent": ok(percent_per_core) if percent_per_core else unavailable(),
        "core_count": ok(psutil.cpu_count(logical=True)),
        "physical_core_count": ok(psutil.cpu_count(logical=False)) if psutil.cpu_count(logical=False) else unavailable(),
        "architecture": ok(arch) if arch else unavailable(),
        "model": ok(model) if model else unavailable(),
        "frequency_current_mhz": ok(round(sum(cur) / len(cur), 1)) if cur else unavailable(),
        "frequency_min_mhz": ok(min(mn)) if mn else unavailable(),
        "frequency_max_mhz": ok(max(mx)) if mx else unavailable(),
        "load_average": load_avg,
        "top_process": top_process,
    }


def _top_process_by(kind: str):
    best = None
    try:
        for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
            try:
                info = p.info
                metric = info.get("cpu_percent" if kind == "cpu" else "memory_percent") or 0
                if best is None or metric > best["metric"]:
                    best = {"pid": info["pid"], "name": info["name"], "metric": round(metric, 1)}
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    except Exception:
        return unavailable()
    if best is None:
        return unavailable()
    return ok(best)


def get_ram_info():
    vm = psutil.virtual_memory()
    swap = psutil.swap_memory()

    data = {
        "total_bytes": ok(vm.total),
        "used_bytes": ok(vm.used),
        "available_bytes": ok(vm.available),
        "free_bytes": ok(vm.free),
        "percent_used": ok(vm.percent),
        "top_process": _top_process_by("ram"),
    }

    if swap.total > 0:
        data["swap_total_bytes"] = ok(swap.total)
        data["swap_used_bytes"] = ok(swap.used)
        data["swap_free_bytes"] = ok(swap.free)
        data["swap_percent"] = ok(swap.percent)
    else:
        for k in ("swap_total_bytes", "swap_used_bytes", "swap_free_bytes", "swap_percent"):
            data[k] = unavailable()

    return data


def get_uptime():
    seconds = time.time() - _BOOT_TIME
    return ok(_format_duration(seconds))


def _format_duration(seconds: float):
    seconds = int(seconds)
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, secs = divmod(rem, 60)
    return {"days": days, "hours": hours, "minutes": minutes, "seconds": secs, "total_seconds": int(seconds)}


def get_android_info():
    """Informações do Android/Termux. IMEI, número de telefone e outros
    identificadores sensíveis NUNCA são coletados aqui, de propósito."""
    manufacturer = run_cmd(["getprop", "ro.product.manufacturer"])
    model = run_cmd(["getprop", "ro.product.model"])
    android_version = run_cmd(["getprop", "ro.build.version.release"])
    sdk = run_cmd(["getprop", "ro.build.version.sdk"])
    hostname = platform.node() or None
    kernel = platform.release() or None
    termux_version = run_cmd(["termux-info"])  # texto longo; só indicamos presença

    return {
        "manufacturer": ok(manufacturer) if manufacturer else unavailable(),
        "model": ok(model) if model else unavailable(),
        "android_version": ok(android_version) if android_version else unavailable(),
        "sdk": ok(sdk) if sdk else unavailable(),
        "architecture": ok(platform.machine()),
        "kernel": ok(kernel) if kernel else unavailable(),
        "hostname": ok(hostname) if hostname else unavailable(),
        "termux_api_available": ok(termux_version is not None),
        "uptime": get_uptime(),
    }
