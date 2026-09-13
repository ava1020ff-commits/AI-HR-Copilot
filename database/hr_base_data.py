"""在职、离职和 HC 基础数据的 SQLite 持久化访问层。"""

import json
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

from database.jobs import get_db_path

DATASETS = ("active", "departed", "hc")


def save_base_data(datasets: dict[str, list[dict[str, str]]], db_path: Path | None = None) -> None:
    if set(datasets) != set(DATASETS):
        raise ValueError("基础数据必须同时包含在职人员、离职人员和 HC。")
    path = db_path or get_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()
    with closing(sqlite3.connect(path, timeout=10)) as connection:
        with connection:
            connection.execute("""CREATE TABLE IF NOT EXISTS hr_base_data (
                dataset TEXT PRIMARY KEY CHECK(dataset IN ('active','departed','hc')),
                payload TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )""")
            for name in DATASETS:
                payload = json.dumps(datasets[name], ensure_ascii=False, sort_keys=True)
                connection.execute(
                    "INSERT INTO hr_base_data(dataset,payload,updated_at) VALUES(?,?,?) "
                    "ON CONFLICT(dataset) DO UPDATE SET payload=excluded.payload,updated_at=excluded.updated_at",
                    (name, payload, now),
                )


def load_base_data(db_path: Path | None = None) -> dict[str, object]:
    path = db_path or get_db_path()
    empty = {"active": [], "departed": [], "hc": [], "updated_at": None}
    if not path.exists():
        return empty
    with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)) as connection:
        exists = connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='hr_base_data'").fetchone()
        if not exists:
            return empty
        rows = connection.execute("SELECT dataset,payload,updated_at FROM hr_base_data").fetchall()
    result = dict(empty)
    timestamps = []
    for name, payload, updated_at in rows:
        try:
            data = json.loads(payload)
            if name not in DATASETS or not isinstance(data, list) or any(not isinstance(item, dict) for item in data):
                raise ValueError
        except (json.JSONDecodeError, TypeError, ValueError):
            raise ValueError("基础数据记录损坏，请重新上传。") from None
        result[name] = data
        timestamps.append(updated_at)
    result["updated_at"] = max(timestamps) if timestamps else None
    return result
