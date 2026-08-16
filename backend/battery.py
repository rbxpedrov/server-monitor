"""
Bateria — depende do pacote termux-api + app Termux:API instalado.
Sem isso, tudo fica marcado como indisponível (não inventamos nada).
Instalação: pkg install termux-api  (e instalar o app "Termux:API" pela Play Store/F-Droid)
"""
import json

from .utils import ok, unavailable, run_cmd


def get_battery_info():
    raw = run_cmd(["termux-battery-status"], timeout=5)
    if raw is None:
        return {
            "percentage": unavailable(),
            "charging": unavailable(),
            "temperature_celsius": unavailable(),
            "voltage_mv": unavailable(),
            "health": unavailable(),
            "technology": unavailable(),
            "status": unavailable(),
            "current_ma": unavailable(),
            "note": "termux-api não disponível — instale 'pkg install termux-api' e o app Termux:API",
        }

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {
            "percentage": unavailable(),
            "charging": unavailable(),
            "temperature_celsius": unavailable(),
            "voltage_mv": unavailable(),
            "health": unavailable(),
            "technology": unavailable(),
            "status": unavailable(),
            "current_ma": unavailable(),
        }

    status = data.get("status")  # "CHARGING", "DISCHARGING", "FULL", "NOT_CHARGING"
    charging = status in ("CHARGING", "FULL") if status else None

    def _field(key):
        val = data.get(key)
        return ok(val) if val is not None else unavailable()

    return {
        "percentage": _field("percentage"),
        "charging": ok(charging) if charging is not None else unavailable(),
        "temperature_celsius": _field("temperature"),
        "voltage_mv": _field("voltage") if "voltage" in data else _field("voltage_mv"),
        "health": _field("health"),
        "technology": _field("technology"),
        "status": _field("status"),
        "current_ma": _field("current"),
        # ciclo de carga e capacidade real (mAh) não são expostos pela
        # API do Android/Termux -> ficam sempre indisponíveis
        "cycle_count": unavailable(),
        "capacity_mah": unavailable(),
    }
