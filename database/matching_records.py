"""匹配页面只读已保存岗位和已确认候选人；不创建库或变更招聘状态。"""

import json
import sqlite3
from contextlib import closing
from pathlib import Path

from database.jobs import get_candidate_db_path, get_db_path


def _read(path: Path, table: str, label: str) -> list[dict]:
    if not path.exists():
        return []
    # table 和 label 只由本模块固定调用传入，不接受用户输入。
    with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)) as connection:
        exists = connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone()
        if not exists:
            return []
        columns = {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}
        metadata = ", work_location, salary_range" if table == "jd_jobs" and {"work_location", "salary_range"} <= columns else ""
        rows = connection.execute(f"SELECT id, {label}, parsed_json, mode{metadata} FROM {table} ORDER BY id DESC").fetchall()
    result = []
    for row in rows:
        identifier, name, payload, mode = row[:4]
        try:
            data = json.loads(payload)
            if not isinstance(data, dict):
                raise ValueError("invalid record")
        except (json.JSONDecodeError, ValueError, TypeError):
            raise ValueError("数据库存在无效 JSON 记录，请先检查已保存数据。") from None
        record = {"id": identifier, "label": name, "data": data, "mode": mode}
        if len(row) == 6:
            if row[4]:
                record["work_location"] = row[4]
            if row[5]:
                record["salary_range"] = row[5]
        result.append(record)
    return result


def list_jobs() -> list[dict]:
    return _read(get_db_path(), "jd_jobs", "job_title")


def list_candidates() -> list[dict]:
    path = get_candidate_db_path()
    return _read(path, "candidates", "candidate_name")
