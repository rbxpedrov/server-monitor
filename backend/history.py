"""
Histórico local de métricas — SQLite simples, nunca enviado ao GitHub.
Guarda amostras leves (não tudo o JSON completo) pra não pesar no
armazenamento do celular nem no desempenho.
"""
import sqlite3
import time
from contextlib import contextmanager

from . import config

_SCHEMA = """
CREATE TABLE IF NOT EXISTS metrics (
    ts REAL NOT NULL,
    cpu_percent REAL,
    ram_percent REAL,
    battery_percent REAL,
    temp_celsius REAL,
    ping_ms REAL,
    storage_percent REAL,
    players_online INTEGER
);
CREATE INDEX IF NOT EXISTS idx_metrics_ts ON metrics(ts);

CREATE TABLE IF NOT EXISTS events (
    ts REAL NOT NULL,
    level TEXT NOT NULL,
    message TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_events_ts ON events(ts);
"""


@contextmanager
def _conn():
    conn = sqlite3.connect(str(config.HISTORY_DB))
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with _conn() as conn:
        conn.executescript(_SCHEMA)


def insert_sample(cpu, ram, battery, temp, ping, storage, players):
    with _conn() as conn:
        conn.execute(
            "INSERT INTO metrics (ts, cpu_percent, ram_percent, battery_percent, "
            "temp_celsius, ping_ms, storage_percent, players_online) VALUES (?,?,?,?,?,?,?,?)",
            (time.time(), cpu, ram, battery, temp, ping, storage, players),
        )


def add_event(level: str, message: str):
    with _conn() as conn:
        conn.execute("INSERT INTO events (ts, level, message) VALUES (?,?,?)", (time.time(), level, message))


def get_events(limit=50):
    with _conn() as conn:
        rows = conn.execute("SELECT ts, level, message FROM events ORDER BY ts DESC LIMIT ?", (limit,)).fetchall()
    return [{"ts": r[0], "level": r[1], "message": r[2]} for r in rows]


PERIODS = {
    "5m": 5 * 60,
    "1h": 60 * 60,
    "6h": 6 * 60 * 60,
    "24h": 24 * 60 * 60,
}


def get_series(period: str = "1h"):
    seconds = PERIODS.get(period, PERIODS["1h"])
    since = time.time() - seconds
    with _conn() as conn:
        rows = conn.execute(
            "SELECT ts, cpu_percent, ram_percent, battery_percent, temp_celsius, "
            "ping_ms, storage_percent, players_online FROM metrics WHERE ts >= ? ORDER BY ts ASC",
            (since,),
        ).fetchall()
    return [
        {
            "ts": r[0], "cpu": r[1], "ram": r[2], "battery": r[3],
            "temp": r[4], "ping": r[5], "storage": r[6], "players": r[7],
        }
        for r in rows
    ]


def cleanup_old(retention_hours: int = None):
    retention_hours = retention_hours or config.HISTORY_RETENTION_HOURS
    cutoff = time.time() - retention_hours * 3600
    with _conn() as conn:
        conn.execute("DELETE FROM metrics WHERE ts < ?", (cutoff,))
        conn.execute("DELETE FROM events WHERE ts < ?", (cutoff,))
