"""
Temperatura — lê todos os thermal_zone expostos em /sys/class/thermal.
Nomes de sensores variam MUITO entre fabricantes (Motorola, Samsung, etc),
então listamos tudo que existir e mostramos o 'type' de cada zona pra o
usuário identificar (ex: 'cpu-0-0-usr', 'battery', 'quiet_therm').
"""
from pathlib import Path

from .utils import ok, unavailable
from .battery import get_battery_info

THERMAL_BASE = Path("/sys/class/thermal")


def get_temperature_info():
    zones = []
    if THERMAL_BASE.exists():
        for zone_dir in sorted(THERMAL_BASE.glob("thermal_zone*")):
            try:
                zone_type = (zone_dir / "type").read_text().strip()
                raw_temp = (zone_dir / "temp").read_text().strip()
                temp_c = int(raw_temp) / 1000  # geralmente em millidegrees
                # alguns kernels já reportam em graus inteiros (valor pequeno)
                if abs(temp_c) < 1 and abs(int(raw_temp)) > 0:
                    temp_c = int(raw_temp)
                zones.append({"name": zone_type, "celsius": round(temp_c, 1)})
            except (FileNotFoundError, ValueError, PermissionError):
                continue

    battery = get_battery_info()
    battery_temp = battery.get("temperature_celsius", unavailable())

    result = {
        "battery_celsius": battery_temp,
        "sensors": ok(zones) if zones else unavailable(),
    }

    # atalhos convenientes pro frontend, quando existirem sensores com
    # nomes reconhecíveis de CPU/SoC
    cpu_zone = next((z for z in zones if "cpu" in z["name"].lower()), None)
    soc_zone = next((z for z in zones if "soc" in z["name"].lower() or "gpu" in z["name"].lower()), None)
    result["cpu_celsius"] = ok(cpu_zone["celsius"]) if cpu_zone else unavailable()
    result["soc_celsius"] = ok(soc_zone["celsius"]) if soc_zone else unavailable()

    return result
