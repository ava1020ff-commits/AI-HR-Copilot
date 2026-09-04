"""Dashboard 分析快照及人工阶段记录。"""

import hashlib
import json
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

from database.jobs import get_db_path
from services.matching import calculate_match

STAGES = ("HR人工确认", "进入面试", "Offer")


def _connect(path: Path | None = None) -> sqlite3.Connection:
    path = path or get_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(path, timeout=10)


def _schema(connection: sqlite3.Connection) -> None:
    connection.executescript("""
        CREATE TABLE IF NOT EXISTS match_reports (
            job_id INTEGER NOT NULL,
            candidate_id INTEGER NOT NULL,
            total_score REAL NOT NULL CHECK(total_score BETWEEN 0 AND 100),
            report_json TEXT NOT NULL,
            rubric_hash TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            PRIMARY KEY(job_id, candidate_id)
        );
        CREATE TABLE IF NOT EXISTS application_stages (
            job_id INTEGER NOT NULL,
            candidate_id INTEGER NOT NULL,
            stage TEXT NOT NULL CHECK(stage IN ('HR人工确认','进入面试','Offer')),
            updated_at TEXT NOT NULL,
            PRIMARY KEY(job_id, candidate_id)
        );
    """)


def save_match_report(job_id: int, candidate_id: int, job: dict, candidate: dict, report: dict) -> None:
    """重算报告以防任意总分写入；只保存每个人岗组合的最新快照。"""
    try:
        rubric = {item["dimension"]: [criterion["criterion"] for criterion in item["criteria"]] for item in report["dimensions"]}
        verified = calculate_match(job, candidate, rubric)
    except (KeyError, TypeError):
        raise ValueError("匹配报告格式无效，不能保存。") from None
    if verified != report:
        raise ValueError("匹配报告与岗位能力模型计算结果不一致，不能保存。")
    payload = json.dumps(verified, ensure_ascii=False, sort_keys=True)
    rubric_hash = hashlib.sha256(json.dumps(rubric, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    now = datetime.now(timezone.utc).isoformat()
    with closing(_connect()) as connection:
        with connection:
            _schema(connection)
            connection.execute("""INSERT INTO match_reports
                (job_id,candidate_id,total_score,report_json,rubric_hash,updated_at)
                VALUES (?,?,?,?,?,?) ON CONFLICT(job_id,candidate_id) DO UPDATE SET
                total_score=excluded.total_score, report_json=excluded.report_json,
                rubric_hash=excluded.rubric_hash, updated_at=excluded.updated_at""",
                (job_id, candidate_id, verified["total_score"], payload, rubric_hash, now))


def set_stage(job_id: int, candidate_id: int, stage: str) -> None:
    """仅允许已有匹配报告的组合由 HR 手工登记运营阶段。"""
    if stage not in STAGES:
        raise ValueError("未知招聘阶段。")
    now = datetime.now(timezone.utc).isoformat()
    with closing(_connect()) as connection:
        with connection:
            _schema(connection)
            exists = connection.execute("SELECT 1 FROM match_reports WHERE job_id=? AND candidate_id=?", (job_id, candidate_id)).fetchone()
            if not exists:
                raise ValueError("请先计算并保存该人岗匹配报告。")
            connection.execute("""INSERT INTO application_stages(job_id,candidate_id,stage,updated_at)
                VALUES(?,?,?,?) ON CONFLICT(job_id,candidate_id) DO UPDATE SET
                stage=excluded.stage, updated_at=excluded.updated_at""", (job_id, candidate_id, stage, now))


def read_analytics(path: Path | None = None) -> dict:
    """读取可审计事实；缺表返回空集合，不为图表编造样本。"""
    target = path or get_db_path()
    if not target.exists():
        return {"reports": [], "stages": []}
    with closing(sqlite3.connect(target.resolve().as_uri() + "?mode=ro", uri=True)) as connection:
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        report_rows = connection.execute("SELECT job_id,candidate_id,total_score,report_json,updated_at FROM match_reports").fetchall() if "match_reports" in tables else []
        stage_rows = connection.execute("SELECT job_id,candidate_id,stage,updated_at FROM application_stages").fetchall() if "application_stages" in tables else []
    reports = []
    for job_id, candidate_id, total, payload, updated in report_rows:
        try:
            report = json.loads(payload)
            if not isinstance(report, dict) or float(report["total_score"]) != float(total):
                raise ValueError
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            raise ValueError("Dashboard 检测到无效匹配报告，请检查数据库。") from None
        reports.append({"job_id": job_id, "candidate_id": candidate_id, "total_score": float(total), "report": report, "updated_at": updated})
    return {"reports": reports, "stages": [{"job_id": r[0], "candidate_id": r[1], "stage": r[2], "updated_at": r[3]} for r in stage_rows]}
