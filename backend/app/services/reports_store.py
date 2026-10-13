"""SQLite-backed store for community waterlogging reports.

Reports are unverified community submissions. They are stored with an explicit
``source`` marker and never treated as official incident data. Only a coarse
location, a free-text description and a severity level are collected - no name,
email, phone number or other personal data is requested or stored.
"""

from __future__ import annotations

import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

from ..config import settings

_LOCK = threading.Lock()
_DB_PATH: Path | None = None

SCHEMA = """
CREATE TABLE IF NOT EXISTS reports (
    id            TEXT PRIMARY KEY,
    created_at_utc TEXT NOT NULL,
    zone_id       TEXT,
    zone_name     TEXT,
    latitude      REAL NOT NULL,
    longitude     REAL NOT NULL,
    description   TEXT NOT NULL,
    severity      TEXT NOT NULL,
    source        TEXT NOT NULL DEFAULT 'user-submitted'
);
CREATE INDEX IF NOT EXISTS idx_reports_created ON reports (created_at_utc DESC);
"""


def db_path() -> Path:
    global _DB_PATH
    if _DB_PATH is None:
        _DB_PATH = Path(settings.database_path)
    return _DB_PATH


def _connect() -> sqlite3.Connection:
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=10)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    with _LOCK, _connect() as connection:
        connection.executescript(SCHEMA)


def create_report(
    *,
    latitude: float,
    longitude: float,
    description: str,
    severity: str,
    zone_id: str | None = None,
    zone_name: str | None = None,
) -> dict:
    record = {
        "id": uuid.uuid4().hex,
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "zone_id": zone_id,
        "zone_name": zone_name,
        "latitude": float(latitude),
        "longitude": float(longitude),
        "description": description.strip(),
        "severity": severity,
        "source": "user-submitted",
    }
    with _LOCK, _connect() as connection:
        connection.execute(
            """
            INSERT INTO reports (id, created_at_utc, zone_id, zone_name, latitude,
                                 longitude, description, severity, source)
            VALUES (:id, :created_at_utc, :zone_id, :zone_name, :latitude,
                    :longitude, :description, :severity, :source)
            """,
            record,
        )
    return _decorate(record)


def list_reports(limit: int = 50, zone_id: str | None = None) -> list[dict]:
    safe_limit = max(1, min(int(limit), settings.max_reports_returned))
    query = "SELECT * FROM reports"
    params: list = []
    if zone_id:
        query += " WHERE zone_id = ?"
        params.append(zone_id)
    query += " ORDER BY created_at_utc DESC, rowid DESC LIMIT ?"
    params.append(safe_limit)
    with _LOCK, _connect() as connection:
        rows = connection.execute(query, params).fetchall()
    return [_decorate(dict(row)) for row in rows]


def count_reports() -> int:
    with _LOCK, _connect() as connection:
        row = connection.execute("SELECT COUNT(*) AS n FROM reports").fetchone()
    return int(row["n"]) if row else 0


def health() -> dict:
    try:
        with _LOCK, _connect() as connection:
            connection.execute("SELECT 1").fetchone()
        return {
            "ok": True,
            "path": str(db_path()),
            "reports_count": count_reports(),
        }
    except sqlite3.Error as exc:
        return {"ok": False, "path": str(db_path()), "error": str(exc)}


def _decorate(record: dict) -> dict:
    record["source"] = "user-submitted"
    record["verification"] = "Unverified community submission - not an official record"
    return record
