"""仅保存 HR 确认后的标准化简历，不保存原始文件、原文或照片。"""

import hashlib
import json
import sqlite3
from contextlib import closing
from pathlib import Path

from database.jobs import get_candidate_db_path
from services.resume_parser import validate_resume


def save_candidate(data: dict, mode: str, *, confirmed: bool = False, db_path: Path | None = None) -> int:
    if confirmed is not True:
        raise ValueError("必须经 HR 确认后才能保存。")
    if mode not in ("local", "llm"):
        raise ValueError("未知简历解析模式。")
    data = validate_resume(data, require_name=True)
    payload = json.dumps(data, ensure_ascii=False, sort_keys=True)
    fingerprint = hashlib.sha256((mode + payload).encode("utf-8")).hexdigest()
    path = db_path or get_candidate_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(path, timeout=10)) as connection:
        with connection:
            connection.execute("""CREATE TABLE IF NOT EXISTS candidates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                candidate_name TEXT NOT NULL,
                parsed_json TEXT NOT NULL,
                mode TEXT NOT NULL CHECK (mode IN ('local', 'llm')),
                fingerprint TEXT NOT NULL UNIQUE,
                confirmed_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
            )""")
            connection.execute(
                "INSERT INTO candidates (candidate_name, parsed_json, mode, fingerprint) VALUES (?, ?, ?, ?) "
                "ON CONFLICT(fingerprint) DO NOTHING", (data["candidate_name"], payload, mode, fingerprint),
            )
            return int(connection.execute("SELECT id FROM candidates WHERE fingerprint=?", (fingerprint,)).fetchone()[0])
