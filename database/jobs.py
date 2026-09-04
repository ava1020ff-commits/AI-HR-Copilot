"""JD 解析结果的本地 SQLite 存储。"""

import hashlib
import json
import sqlite3
from contextlib import closing
from pathlib import Path

from services.jd_parser import validate_jd, validate_job
from services.config import get_setting, resolve_data_path

DEFAULT_DB_PATH = resolve_data_path("database/recruitment.sqlite3")


def get_db_path() -> Path:
    return resolve_data_path(get_setting("JD_DATABASE_PATH") or "database/recruitment.sqlite3")


def get_candidate_db_path() -> Path:
    configured = get_setting("RESUME_DATABASE_PATH")
    return resolve_data_path(configured) if configured else get_db_path()


def save_job(jd: str, result: dict, mode: str, db_path: Path | None = None) -> int:
    """在事务中保存；相同 JD、结果和模式的重复提交返回原 ID。"""
    jd = validate_jd(jd)
    result = validate_job(result)
    if mode not in ("mock", "llm"):
        raise ValueError("未知解析模式")
    payload = json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False)
    fingerprint = hashlib.sha256(json.dumps([jd, payload, mode], ensure_ascii=False).encode("utf-8")).hexdigest()
    path = db_path or get_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(path, timeout=10)) as connection:
        with connection:
            connection.execute("""CREATE TABLE IF NOT EXISTS jd_jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_title TEXT NOT NULL,
                source_jd TEXT NOT NULL,
                parsed_json TEXT NOT NULL,
                mode TEXT NOT NULL CHECK (mode IN ('mock', 'llm')),
                fingerprint TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
            )""")
            connection.execute(
                "INSERT INTO jd_jobs (job_title, source_jd, parsed_json, mode, fingerprint) "
                "VALUES (?, ?, ?, ?, ?) ON CONFLICT(fingerprint) DO NOTHING",
                (result["job_title"], jd, payload, mode, fingerprint),
            )
            row = connection.execute("SELECT id FROM jd_jobs WHERE fingerprint = ?", (fingerprint,)).fetchone()
            return int(row[0])
