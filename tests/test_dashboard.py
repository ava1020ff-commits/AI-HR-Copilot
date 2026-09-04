"""Dashboard 统计、持久化和页面测试，使用临时 SQLite。"""

import copy
import sqlite3
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from database.candidates import save_candidate
from database.dashboard import STAGES, read_analytics, save_match_report, set_stage
from database.jobs import save_job
from services.dashboard import HIGH_MATCH_THRESHOLD, dashboard_metrics
from services.matching import calculate_match
from services.resume_parser import FIELDS

PAGE = Path(__file__).resolve().parents[1] / "pages" / "05_招聘分析.py"


def job(name="测试后端岗") -> dict:
    return {"job_title": name, "education": "未提及", "experience": "未提及", "hard_skills": ["Python", "SQL"], "soft_skills": [], "bonus_skills": [], "competency_model": [
        {"dimension": "后端开发", "weight": 60, "description": "使用 Python 开发接口"},
        {"dimension": "数据能力", "weight": 40, "description": "使用 SQL 处理数据"},
    ]}


def candidate(name="合成候选人", practice=True) -> dict:
    return {"candidate_name": name, **{key: [] for key in FIELDS}, "projects": ["使用 Python 开发接口并完成上线"] if practice else [], "skills": ["SQL"] if practice else []}


@pytest.fixture(autouse=True)
def isolated(monkeypatch, tmp_path):
    path = tmp_path / "recruitment.sqlite3"
    monkeypatch.setenv("JD_DATABASE_PATH", str(path))
    monkeypatch.setenv("RESUME_DATABASE_PATH", str(path))


def seed(name="合成候选人", practice=True):
    role, resume = job(), candidate(name, practice)
    job_id = save_job("合成 JD", role, "mock")
    candidate_id = save_candidate(resume, "local", confirmed=True)
    report = calculate_match(role, resume)
    save_match_report(job_id, candidate_id, role, resume, report)
    return job_id, candidate_id, role, resume, report


def test_empty_metrics() -> None:
    metrics = dashboard_metrics([], [], {"reports": [], "stages": []})
    assert metrics["candidate_count"] == metrics["job_count"] == 0
    assert metrics["average_score"] is None and metrics["high_match_count"] == 0
    assert list(metrics["funnel"].values()) == [0, 0, 0, 0, 0]


def test_metrics_and_normalized_dimensions() -> None:
    role = job()
    reports = [
        {"job_id": 1, "candidate_id": 10, "total_score": 80, "report": {"dimensions": [{"dimension": "后端开发", "score": 30, "max_score": 60}]}},
        {"job_id": 1, "candidate_id": 11, "total_score": 60, "report": {"dimensions": [{"dimension": "后端开发", "score": 60, "max_score": 60}]}},
        {"job_id": 2, "candidate_id": 10, "total_score": 90, "report": {"dimensions": [{"dimension": "后端开发", "score": 15, "max_score": 30}]}},
    ]
    stages = [{"job_id": 1, "candidate_id": 10, "stage": "Offer"}, {"job_id": 1, "candidate_id": 11, "stage": "HR人工确认"}]
    metrics = dashboard_metrics([{"id": 1}, {"id": 2}], [{"id": 10}, {"id": 11}], {"reports": reports, "stages": stages})
    assert metrics["average_score"] == pytest.approx(76.67)
    assert metrics["high_match_count"] == 1
    assert metrics["job_averages"] == {1: 70, 2: 90}
    assert metrics["dimension_averages"]["后端开发"] == pytest.approx(66.67)
    assert list(metrics["funnel"].values()) == [2, 2, 2, 1, 1]


def test_high_match_deduplicates_candidate() -> None:
    reports = [{"job_id": job_id, "candidate_id": 1, "total_score": score, "report": {"dimensions": []}} for job_id, score in ((1, HIGH_MATCH_THRESHOLD), (2, 99))]
    metrics = dashboard_metrics([{"id": 1}, {"id": 2}], [{"id": 1}], {"reports": reports, "stages": []})
    assert metrics["high_match_count"] == 1


def test_orphan_reports_excluded() -> None:
    report = {"job_id": 999, "candidate_id": 1, "total_score": 100, "report": {"dimensions": []}}
    metrics = dashboard_metrics([{"id": 1}], [{"id": 1}], {"reports": [report], "stages": []})
    assert metrics["report_count"] == 0 and metrics["orphan_report_count"] == 1


def test_report_persistence_and_latest_snapshot() -> None:
    job_id, candidate_id, role, resume, report = seed()
    assert read_analytics()["reports"][0]["report"] == report
    modified = copy.deepcopy(resume)
    modified["skills"] = ["Python", "SQL"]
    updated = calculate_match(role, modified)
    save_match_report(job_id, candidate_id, role, modified, updated)
    analytics = read_analytics()
    assert len(analytics["reports"]) == 1 and analytics["reports"][0]["report"] == updated


def test_tampered_total_cannot_be_saved() -> None:
    role, resume = job(), candidate()
    report = calculate_match(role, resume)
    report["total_score"] = 100
    with pytest.raises(ValueError):
        save_match_report(1, 1, role, resume, report)


def test_stage_requires_report_and_is_current_value() -> None:
    with pytest.raises(ValueError):
        set_stage(1, 1, "Offer")
    job_id, candidate_id, *_ = seed()
    for stage in STAGES:
        set_stage(job_id, candidate_id, stage)
        assert read_analytics()["stages"] == [{"job_id": job_id, "candidate_id": candidate_id, "stage": stage, "updated_at": read_analytics()["stages"][0]["updated_at"]}]
    with pytest.raises(ValueError):
        set_stage(job_id, candidate_id, "自动淘汰")


def test_page_empty_shows_four_charts() -> None:
    app = AppTest.from_file(str(PAGE), default_timeout=15).run()
    assert not app.exception and len(app.metric) == 4
    assert len(app.get("plotly_chart")) == 4
    assert app.metric[2].value == "暂无数据"


def test_page_data_and_manual_confirmation() -> None:
    seed()
    app = AppTest.from_file(str(PAGE), default_timeout=15).run()
    assert not app.exception and len(app.get("plotly_chart")) == 4
    assert app.metric[0].value == "1" and app.metric[1].value == "1"
    app.button[0].click().run()
    assert app.error
    app.checkbox[0].check()
    app.button[0].click().run()
    assert app.success
    assert read_analytics()["stages"][0]["stage"] == "HR人工确认"


def test_matching_page_saves_report() -> None:
    role, resume = job(), candidate()
    save_job("合成 JD", role, "mock")
    save_candidate(resume, "local", confirmed=True)
    match_page = PAGE.parents[0] / "03_智能匹配.py"
    app = AppTest.from_file(str(match_page), default_timeout=15).run()
    app.button[0].click().run()
    assert not app.exception and len(read_analytics()["reports"]) == 1


def test_navigation() -> None:
    app = AppTest.from_file(str(PAGE.parents[1] / "app.py"), default_timeout=15).run()
    app.switch_page("pages/05_招聘分析.py").run()
    assert not app.exception and app.title[0].value == "Recruitment Dashboard"
