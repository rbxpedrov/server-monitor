"""Lista de processos, com destaque pro processo do Minecraft (java)."""
import psutil

from .utils import ok


def get_processes(sort_by: str = "cpu", limit: int = 30):
    procs = []
    for p in psutil.process_iter(["pid", "name", "username", "cpu_percent", "memory_percent", "create_time", "cmdline"]):
        try:
            info = p.info
            cmdline = " ".join(info.get("cmdline") or [])[:120]
            procs.append({
                "pid": info["pid"],
                "name": info["name"],
                "user": info.get("username"),
                "cpu_percent": round(info.get("cpu_percent") or 0, 1),
                "ram_percent": round(info.get("memory_percent") or 0, 1),
                "running_since": info.get("create_time"),
                "command": cmdline,
                "is_minecraft": "java" in (info.get("name") or "").lower() or "minecraft" in cmdline.lower(),
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    key_map = {
        "cpu": lambda x: x["cpu_percent"],
        "ram": lambda x: x["ram_percent"],
        "pid": lambda x: x["pid"],
        "name": lambda x: (x["name"] or "").lower(),
    }
    key_fn = key_map.get(sort_by, key_map["cpu"])
    procs.sort(key=key_fn, reverse=sort_by in ("cpu", "ram"))

    return ok(procs[:limit])
