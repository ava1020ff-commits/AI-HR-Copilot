"""面试助手读取 JD 原文；数据库连接保持只读。"""

import sqlite3
from contextlib import closing

from database.jobs import get_db_path


def read_jd(job_id: int) -> str:
    path = get_db_path()
    if not path.exists():
        raise ValueError("岗位数据库不存在。")
    with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)) as connection:
        row = connection.execute("SELECT source_jd FROM jd_jobs WHERE id=?", (job_id,)).fetchone()
    if row is None or not isinstance(row[0], str):
        raise ValueError("岗位 JD 已不存在，请重新选择岗位。")
    return row[0]
