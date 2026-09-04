"""匹配规则和页面回归，不读取真实简历或调用 LLM。"""

import copy
import json
import sqlite3
from decimal import Decimal
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from database.candidates import save_candidate
from database.jobs import save_job
from database.matching_records import list_candidates, list_jobs
from services.matching import MatchingError, NO_EVIDENCE, RECOMMENDATIONS, build_rubric, calculate_match
from services.resume_parser import FIELDS

PAGE = Path(__file__).resolve().parents[1] / "pages" / "03_智能匹配.py"


def job() -> dict:
    return {
        "job_title": "测试产品岗位", "education": "本科", "experience": "未提及",
        "hard_skills": [], "soft_skills": [], "bonus_skills": [],
        "competency_model": [
            {"dimension": "产品能力", "weight": 30, "description": "需求分析"},
            {"dimension": "AI能力", "weight": 25, "description": "RAG"},
            {"dimension": "项目经验", "weight": 20, "description": "项目交付"},
            {"dimension": "数据能力", "weight": 10, "description": "SQL"},
            {"dimension": "沟通协作", "weight": 10, "description": "沟通协作"},
            {"dimension": "教育背景", "weight": 5, "description": "本科及以上"},
        ],
    }


def candidate() -> dict:
    return {
        "candidate_name": "合成测试甲", "education": ["测试大学 本科 计算机"],
        "work_experience": ["负责需求分析并输出需求文档", "使用 SQL 实现数据报表", "协调跨部门沟通并完成需求评审"],
        "internships": [], "projects": ["使用 RAG 实现知识检索", "负责项目交付并完成验收"],
        "skills": [], "certificates": [],
    }


@pytest.fixture(autouse=True)
def isolated_db(monkeypatch, tmp_path):
    monkeypatch.setenv("JD_DATABASE_PATH", str(tmp_path / "jobs.sqlite3"))
    monkeypatch.setenv("RESUME_DATABASE_PATH", str(tmp_path / "candidates.sqlite3"))


def test_weighted_total_and_exact_evidence() -> None:
    resume = candidate()
    result = calculate_match(job(), resume)
    assert result["total_score"] == 100
    assert result["recommendation"] == "建议进一步评估"
    assert Decimal(str(result["total_score"])) == sum(Decimal(str(d["score"])) for d in result["dimensions"])
    for dimension in result["dimensions"]:
        assert 0 <= dimension["score"] <= dimension["max_score"]
        assert 0 <= dimension["confidence"] <= 1
        for evidence in dimension["evidence_sources"]:
            field, index = evidence["source"].rstrip("]").split("[")
            assert evidence["quote"] in resume[field][int(index)]
            assert evidence["quote"] in dimension["evidence"]


def test_no_evidence_is_insufficient_not_rejection() -> None:
    result = calculate_match(job(), {key: [] for key in FIELDS})
    assert result["total_score"] == 0
    assert result["recommendation"] == "信息不足"
    assert all(d["evidence"] == [NO_EVIDENCE] and d["confidence"] == 0 for d in result["dimensions"])
    assert result["questions_to_verify"]


@pytest.mark.parametrize("record", ["Python工程师", "担任产品经理", "数据分析师", "RAG developer", "负责人的职位是AI专家", "SQL开发", "高级RAG开发", "AI架构师"])
def test_titles_never_imply_skills(record: str) -> None:
    resume = {key: [] for key in FIELDS}
    for key in ("skills", "projects", "work_experience"):
        resume[key] = [record]
    assert calculate_match(job(), resume)["total_score"] == 0


def test_job_title_does_not_change_score() -> None:
    first = job()
    second = copy.deepcopy(first)
    second["job_title"] = "AI Python SQL 产品经理"
    assert calculate_match(first, candidate()) == calculate_match(second, candidate())


def test_sensitive_properties_and_name_not_used() -> None:
    resume = candidate()
    expected = calculate_match(job(), resume)
    resume.update({"candidate_name": "另一姓名", "age": 80, "gender": "女", "marital_status": "已婚", "photo": "photo.png"})
    assert calculate_match(job(), resume) == expected


def test_sensitive_records_are_not_evidence() -> None:
    resume = {key: [] for key in FIELDS}
    resume["projects"] = ["性别女，使用 RAG 完成项目交付", "已育，负责需求分析"]
    result = calculate_match(job(), resume)
    assert result["total_score"] == 0
    assert "已育" not in json.dumps(result, ensure_ascii=False)


@pytest.mark.parametrize("record", ["没有使用 SQL 的经验", "不具备需求分析经验", "never used RAG", "未参与项目交付"])
def test_negative_statements_not_positive_evidence(record: str) -> None:
    resume = {key: [] for key in FIELDS}
    resume["work_experience"] = [record]
    assert calculate_match(job(), resume)["total_score"] == 0


def test_skill_self_claim_partial_score_and_duplicates() -> None:
    resume = {key: [] for key in FIELDS}
    resume["skills"] = ["需求分析", "RAG", "项目交付", "SQL", "沟通协作"]
    result = calculate_match(job(), resume)
    assert result["total_score"] == 47.5
    assert result["recommendation"] == "匹配度较低"
    assert result["recommendation"] in RECOMMENDATIONS
    resume["skills"] *= 5
    assert calculate_match(job(), resume) == result


def test_rounding_and_mixed_indicators() -> None:
    rubric = build_rubric(job())
    rubric["产品能力"] = ["需求分析", "用户研究", "产品设计"]
    result = calculate_match(job(), candidate(), rubric)
    assert result["dimensions"][0]["score"] == 10
    assert result["total_score"] == 80


def test_unknown_dimension_no_invented_evidence() -> None:
    role = job()
    role["competency_model"] = [{"dimension": "未知能力", "weight": 100, "description": "未明确"}]
    result = calculate_match(role, candidate())
    assert result["total_score"] == 0 and result["recommendation"] == "信息不足"


@pytest.mark.parametrize("model", [[], [{"dimension": "年龄", "weight": 100, "description": "年轻"}], [{"dimension": "数据", "weight": 90, "description": "SQL"}]])
def test_invalid_model_rejected(model: list) -> None:
    role = job()
    role["competency_model"] = model
    with pytest.raises(MatchingError):
        calculate_match(role, candidate())


def test_sensitive_custom_rubric_rejected() -> None:
    rubric = build_rubric(job())
    rubric["产品能力"] = ["婚育"]
    with pytest.raises(MatchingError):
        calculate_match(job(), candidate(), rubric)


def test_education_in_progress_not_assumed_complete() -> None:
    resume = candidate()
    resume["education"] = ["本科在读"]
    assert calculate_match(job(), resume)["dimensions"][-1]["score"] == 0


def test_readers_do_not_create_database(tmp_path) -> None:
    assert list_jobs() == [] and list_candidates() == []
    assert not (tmp_path / "jobs.sqlite3").exists()


def test_database_selection_and_read_only(tmp_path) -> None:
    save_job("合成JD", job(), "mock")
    save_candidate(candidate(), "local", confirmed=True)
    assert list_jobs()[0]["data"] == job()
    assert list_candidates()[0]["data"] == candidate()
    before = (tmp_path / "candidates.sqlite3").read_bytes()
    calculate_match(list_jobs()[0]["data"], list_candidates()[0]["data"])
    assert (tmp_path / "candidates.sqlite3").read_bytes() == before


def test_page_empty_state() -> None:
    app = AppTest.from_file(str(PAGE), default_timeout=15).run()
    assert not app.exception and app.warning
    assert not app.selectbox


def test_page_computation_and_selection_change() -> None:
    save_job("合成JD", job(), "mock")
    first = candidate()
    save_candidate(first, "local", confirmed=True)
    second = {"candidate_name": "合成测试乙", **{key: [] for key in FIELDS}}
    save_candidate(second, "local", confirmed=True)
    app = AppTest.from_file(str(PAGE), default_timeout=15).run()
    assert not app.exception and len(app.selectbox) == 2
    app.button[0].click().run()
    assert not app.exception and app.metric[0].value == "0.0"
    app.selectbox[1].select(1).run()
    assert not app.metric
    app.button[0].click().run()
    assert not app.exception and app.metric[0].value == "100.0"
    assert all("淘汰" not in button.label for button in app.button)


def test_navigation() -> None:
    app = AppTest.from_file(str(PAGE.parents[1] / "app.py"), default_timeout=15).run()
    app.switch_page("pages/03_智能匹配.py").run()
    assert not app.exception and app.title[0].value == "人岗匹配"
