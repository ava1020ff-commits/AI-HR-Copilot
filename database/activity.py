"""首页所需 AI 操作日志；与招聘主库共同持久化。"""

import sqlite3
from contextlib import closing
from datetime import datetime, timezone

from database.jobs import get_db_path

AI_ACTIONS = ("resume_screening", "boss_message", "interview_questions", "candidate_analysis", "jd_optimization")


def record_ai_usage(action: str, *, job_id: int | None = None, candidate_id: int | None = None) -> None:
    if action not in AI_ACTIONS:
        raise ValueError("未知 AI 操作类型。")
    path = get_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(path, timeout=10)) as connection:
        with connection:
            connection.execute("""CREATE TABLE IF NOT EXISTS ai_usage_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action TEXT NOT NULL,
                job_id INTEGER,
                candidate_id INTEGER,
                created_at TEXT NOT NULL
            )""")
            connection.execute(
                "INSERT INTO ai_usage_log (action, job_id, candidate_id, created_at) VALUES (?, ?, ?, ?)",
                (action, job_id, candidate_id, datetime.now(timezone.utc).isoformat()),
            )


def list_ai_usage() -> list[dict]:
    path = get_db_path()
    if not path.exists():
        return []
    with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)) as connection:
        exists = connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='ai_usage_log'").fetchone()
        if not exists:
            return []
        rows = connection.execute("SELECT action, job_id, candidate_id, created_at FROM ai_usage_log ORDER BY id DESC").fetchall()
    return [{"action": row[0], "job_id": row[1], "candidate_id": row[2], "created_at": row[3]} for row in rows]


def try_record_ai_usage(action: str, *, job_id: int | None = None, candidate_id: int | None = None) -> bool:
    """日志写入失败不应让已经完成的业务操作失败。"""
    try:
        record_ai_usage(action, job_id=job_id, candidate_id=candidate_id)
        return True
    except (sqlite3.Error, OSError):
        return False
