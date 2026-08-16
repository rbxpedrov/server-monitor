"""Calcula os alertas ativos a partir do snapshot atual. Alertas somem
sozinhos quando a condição normaliza, porque são recalculados a cada chamada."""
from . import config


def compute_alerts(cpu, ram, storage, battery, temperature, network, minecraft):
    alerts = []

    cpu_val = cpu.get("usage_total_percent", {}).get("value")
    if cpu_val is not None and cpu_val >= config.ALERT_CPU_PERCENT:
        alerts.append({"level": "warning", "icon": "⚠", "message": f"CPU acima de {config.ALERT_CPU_PERCENT:.0f}% ({cpu_val:.0f}%)"})

    ram_val = ram.get("percent_used", {}).get("value")
    if ram_val is not None and ram_val >= config.ALERT_RAM_PERCENT:
        alerts.append({"level": "warning", "icon": "⚠", "message": f"RAM acima de {config.ALERT_RAM_PERCENT:.0f}% ({ram_val:.0f}%)"})

    storage_val = storage.get("percent_used", {}).get("value")
    if storage_val is not None and storage_val >= config.ALERT_STORAGE_PERCENT:
        alerts.append({"level": "warning", "icon": "⚠", "message": f"Armazenamento quase cheio ({storage_val:.0f}%)"})

    batt_val = battery.get("percentage", {}).get("value")
    charging = battery.get("charging", {}).get("value")
    if batt_val is not None and batt_val <= config.ALERT_BATTERY_LOW and not charging:
        alerts.append({"level": "warning", "icon": "⚠", "message": f"Bateria baixa ({batt_val:.0f}%)"})

    batt_temp = battery.get("temperature_celsius", {}).get("value")
    if batt_temp is not None and batt_temp >= config.ALERT_TEMP_CELSIUS:
        alerts.append({"level": "critical", "icon": "🔥", "message": f"Temperatura elevada ({batt_temp:.0f}°C)"})

    online = network.get("internet_online", {}).get("value")
    if online is False:
        alerts.append({"level": "critical", "icon": "🔴", "message": "Internet desconectada"})

    mc_online = minecraft.get("online", {}).get("value")
    if mc_online is False:
        alerts.append({"level": "critical", "icon": "🔴", "message": "Minecraft offline"})

    return alerts
