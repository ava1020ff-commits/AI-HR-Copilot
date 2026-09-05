"""JD 解析结果的本地 SQLite 存储。"""

import hashlib
import json
import sqlite3
from contextlib import closing
from pathlib import Path

from services.jd_parser import validate_jd, validate_job
from services.config import get_setting, resolve_data_path

DEFAULT_DB_PATH = resolve_data_path("database/recruitment.sqlite3")


def _ensure_jobs_table(connection: sqlite3.Connection) -> None:
    connection.execute("""CREATE TABLE IF NOT EXISTS jd_jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        job_title TEXT NOT NULL,
        source_jd TEXT NOT NULL,
        parsed_json TEXT NOT NULL,
        mode TEXT NOT NULL CHECK (mode IN ('mock', 'local', 'llm')),
        fingerprint TEXT NOT NULL UNIQUE,
        created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
    )""")
    schema = connection.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='jd_jobs'"
    ).fetchone()[0]
    if "'local'" not in schema:
        connection.executescript("""
            ALTER TABLE jd_jobs RENAME TO jd_jobs_legacy;
            CREATE TABLE jd_jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_title TEXT NOT NULL, source_jd TEXT NOT NULL, parsed_json TEXT NOT NULL,
                mode TEXT NOT NULL CHECK (mode IN ('mock','local','llm')),
                fingerprint TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
            );
            INSERT INTO jd_jobs SELECT * FROM jd_jobs_legacy;
            DROP TABLE jd_jobs_legacy;
        """)
    columns = {row[1] for row in connection.execute("PRAGMA table_info(jd_jobs)")}
    if "work_location" not in columns:
        connection.execute("ALTER TABLE jd_jobs ADD COLUMN work_location TEXT NOT NULL DEFAULT ''")
    if "salary_range" not in columns:
        connection.execute("ALTER TABLE jd_jobs ADD COLUMN salary_range TEXT NOT NULL DEFAULT ''")


def _validated_payload(jd: str, result: dict, mode: str) -> tuple[str, dict, str, str]:
    jd = validate_jd(jd)
    result = validate_job(result)
    if mode not in ("mock", "local", "llm"):
        raise ValueError("未知解析模式")
    payload = json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False)
    fingerprint = hashlib.sha256(json.dumps([jd, payload, mode], ensure_ascii=False).encode("utf-8")).hexdigest()
    return jd, result, payload, fingerprint


def get_db_path() -> Path:
    return resolve_data_path(get_setting("JD_DATABASE_PATH") or "database/recruitment.sqlite3")


def get_candidate_db_path() -> Path:
    configured = get_setting("RESUME_DATABASE_PATH")
    return resolve_data_path(configured) if configured else get_db_path()


def save_job(
    jd: str,
    result: dict,
    mode: str,
    db_path: Path | None = None,
    work_location: str = "",
    salary_range: str = "",
) -> int:
    """在事务中保存；相同 JD、结果和模式的重复提交返回原 ID。"""
    jd, result, payload, fingerprint = _validated_payload(jd, result, mode)
    work_location = work_location.strip()[:200]
    salary_range = salary_range.strip()[:200]
    fingerprint = hashlib.sha256(
        json.dumps([jd, payload, mode, work_location, salary_range], ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    path = db_path or get_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(path, timeout=10)) as connection:
        with connection:
            _ensure_jobs_table(connection)
            connection.execute(
                "INSERT INTO jd_jobs (job_title, source_jd, parsed_json, mode, fingerprint, work_location, salary_range) "
                "VALUES (?, ?, ?, ?, ?, ?, ?) ON CONFLICT(fingerprint) DO NOTHING",
                (result["job_title"], jd, payload, mode, fingerprint, work_location, salary_range),
            )
            row = connection.execute("SELECT id FROM jd_jobs WHERE fingerprint = ?", (fingerprint,)).fetchone()
            return int(row[0])


def list_saved_jobs(db_path: Path | None = None) -> list[dict]:
    """Return editable job records including their original JD."""
    path = db_path or get_db_path()
    if not path.exists():
        return []
    with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)) as connection:
        exists = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='jd_jobs'"
        ).fetchone()
        if not exists:
            return []
        columns = {row[1] for row in connection.execute("PRAGMA table_info(jd_jobs)")}
        metadata = ", work_location, salary_range" if {"work_location", "salary_range"} <= columns else ""
        rows = connection.execute(
            f"SELECT id, job_title, source_jd, parsed_json, mode{metadata} FROM jd_jobs ORDER BY id DESC"
        ).fetchall()
    records = []
    for row in rows:
        identifier, title, source_jd, payload, mode = row[:5]
        work_location, salary_range = row[5:] if len(row) == 7 else ("", "")
        records.append({
            "id": int(identifier), "job_title": title, "source_jd": source_jd,
            "result": validate_job(json.loads(payload)), "mode": mode,
            "work_location": work_location, "salary_range": salary_range,
        })
    return records


def update_job(
    job_id: int,
    jd: str,
    result: dict,
    mode: str,
    db_path: Path | None = None,
    work_location: str = "",
    salary_range: str = "",
) -> int:
    """Replace one saved job while retaining its ID and related records."""
    if not isinstance(job_id, int) or isinstance(job_id, bool) or job_id < 1:
        raise ValueError("无效岗位 ID")
    jd, result, payload, fingerprint = _validated_payload(jd, result, mode)
    work_location = work_location.strip()[:200]
    salary_range = salary_range.strip()[:200]
    fingerprint = hashlib.sha256(
        json.dumps([jd, payload, mode, work_location, salary_range], ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    path = db_path or get_db_path()
    if not path.exists():
        raise ValueError("岗位不存在")
    with closing(sqlite3.connect(path, timeout=10)) as connection:
        with connection:
            _ensure_jobs_table(connection)
            cursor = connection.execute(
                "UPDATE jd_jobs SET job_title=?, source_jd=?, parsed_json=?, mode=?, fingerprint=?, "
                "work_location=?, salary_range=? WHERE id=?",
                (result["job_title"], jd, payload, mode, fingerprint, work_location, salary_range, job_id),
            )
            if cursor.rowcount != 1:
                raise ValueError("岗位不存在")
    return job_id
