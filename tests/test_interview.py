"""面试助手使用合成数据，覆盖原文引用、报告一致性和页面行为。"""

import copy
import json
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from database.candidates import save_candidate
from database.jobs import save_job
from database.matching_records import list_candidates, list_jobs
from services.interview import CATEGORIES, InterviewError, generate_interview
from services.matching import calculate_match
from services.resume_parser import FIELDS

PAGE = Path(__file__).resolve().parents[1] / "pages" / "04_面试助手.py"
JD = "岗位职责：使用 RAG 构建知识库检索，负责 SQL 报表的数据准确性。"


def job() -> dict:
    return {"job_title": "测试知识库岗位", "education": "未提及", "experience": "未提及", "hard_skills": ["RAG", "SQL"], "soft_skills": [], "bonus_skills": [], "competency_model": [
        {"dimension": "AI能力", "weight": 60, "description": "使用 RAG 构建可评测的知识检索"},
        {"dimension": "数据能力", "weight": 40, "description": "使用 SQL 验证数据准确性"},
    ]}


def candidate() -> dict:
    return {"candidate_name": "合成面试甲", **{key: [] for key in FIELDS}, "projects": ["星河知识库：使用 RAG 实现文档检索并比较召回结果"], "work_experience": ["晨光报表：使用 SQL 实现销售汇总并核验重复数据"]}


@pytest.fixture(autouse=True)
def isolation(monkeypatch, tmp_path):
    monkeypatch.setenv("JD_DATABASE_PATH", str(tmp_path / "jobs.sqlite3"))
    monkeypatch.setenv("RESUME_DATABASE_PATH", str(tmp_path / "candidates.sqlite3"))


def test_categories_fields_and_exact_quotes() -> None:
    role, resume = job(), candidate()
    guide = generate_interview(role, JD, resume, calculate_match(role, resume))
    assert set(guide["categories"]) == set(CATEGORIES)
    questions = []
    for items in guide["categories"].values():
        assert items
        for item in items:
            assert all(item[key] for key in ("question", "purpose", "evaluation_dimension", "follow_up", "good_signals", "risk_signals"))
            source = item["sources"]["resume"]
            field, index = source["source"].rstrip("]").split("[")
            assert source["quote"] == resume[field][int(index)]
            assert source["quote"] in item["question"]
            assert item["sources"]["jd"] in JD
            assert item["evaluation_dimension"] in ("AI能力", "数据能力")
            questions.append(item["question"])
    assert len(questions) == len(set(questions))


def test_resume_change_changes_questions() -> None:
    first = candidate()
    second = candidate()
    second["projects"] = ["海风客服：使用 RAG 实现故障检索"]
    left = generate_interview(job(), JD, first, calculate_match(job(), first))
    right = generate_interview(job(), JD, second, calculate_match(job(), second))
    assert left != right
    assert "海风客服" in json.dumps(right, ensure_ascii=False)
    assert "星河知识库" not in json.dumps(right, ensure_ascii=False)


def test_jd_changes_question_context() -> None:
    resume = candidate()
    report = calculate_match(job(), resume)
    assert generate_interview(job(), JD, resume, report) != generate_interview(job(), "使用 RAG 对设备维修文档检索，SQL 核实库存", resume, report)


def test_star_has_situation_task_action_result() -> None:
    resume = candidate()
    items = generate_interview(job(), JD, resume, calculate_match(job(), resume))["categories"]["STAR行为面试"]
    assert all(all(marker in item["question"] for marker in ("S（", "T（", "A（", "R（")) for item in items)


def test_report_gap_drives_risk_questions() -> None:
    resume = candidate()
    resume["work_experience"] = []
    report = calculate_match(job(), resume)
    items = generate_interview(job(), JD, resume, report)["categories"]["风险验证"]
    assert items[0]["evaluation_dimension"] == "数据能力"
    assert "暂无明确证据" in items[0]["question"] and "SQL" in items[0]["question"]
    assert "信息缺口" in items[0]["purpose"]


def test_skills_only_does_not_invent_experience() -> None:
    resume = {"candidate_name": "合成乙", **{key: [] for key in FIELDS}, "skills": ["RAG"]}
    guide = generate_interview(job(), JD, resume, calculate_match(job(), resume))
    assert guide["categories"]["经历真实性验证"] == []
    assert guide["categories"]["STAR行为面试"] == []
    assert guide["omissions"]
    assert guide["categories"]["专业能力"]


def test_no_anchors_refuses_generic_questions() -> None:
    resume = {key: [] for key in FIELDS}
    with pytest.raises(InterviewError, match="职业信息"):
        generate_interview(job(), JD, resume, calculate_match(job(), resume))


def test_report_tampering_and_stale_evidence_rejected() -> None:
    resume = candidate()
    report = calculate_match(job(), resume)
    bad = copy.deepcopy(report)
    bad["total_score"] = 999
    with pytest.raises(InterviewError):
        generate_interview(job(), JD, resume, bad)
    resume["projects"] = ["新项目：使用 RAG 构建检索"]
    with pytest.raises(InterviewError):
        generate_interview(job(), JD, resume, report)


def test_custom_report_rubric_is_preserved() -> None:
    resume = candidate()
    report = calculate_match(job(), resume, {"AI能力": ["RAG", "模型评测"], "数据能力": ["SQL"]})
    guide = generate_interview(job(), JD, resume, report)
    assert "模型评测" in json.dumps(guide, ensure_ascii=False)


def test_sensitive_information_not_quoted() -> None:
    resume = candidate()
    resume["projects"].append("已婚，女，使用 RAG 开发项目")
    resume.update({"age": 99, "gender": "女", "marital_status": "已婚"})
    guide = generate_interview(job(), JD + " 年龄30岁；性别男", resume, calculate_match(job(), resume))
    encoded = json.dumps(guide, ensure_ascii=False)
    assert "已婚" not in encoded and "性别男" not in encoded and "30岁" not in encoded


def test_page_empty_state() -> None:
    app = AppTest.from_file(str(PAGE), default_timeout=15).run()
    assert not app.exception and app.warning


def test_page_generates_and_clears_on_change() -> None:
    save_job(JD, job(), "mock")
    save_candidate(candidate(), "local", confirmed=True)
    second = candidate()
    second["candidate_name"] = "合成面试乙"
    second["projects"] = ["海风客服：使用 RAG 完成客服检索"]
    save_candidate(second, "local", confirmed=True)
    app = AppTest.from_file(str(PAGE), default_timeout=15).run()
    app.button[0].click().run()
    assert not app.exception and app.success and app.json
    app.selectbox[1].select(1).run()
    assert not app.success and "interview_result" not in app.session_state


def test_page_reuses_matching_report() -> None:
    save_job(JD, job(), "mock")
    save_candidate(candidate(), "local", confirmed=True)
    saved_job, saved_candidate = list_jobs()[0], list_candidates()[0]
    report = calculate_match(saved_job["data"], saved_candidate["data"], {"AI能力": ["RAG", "评测"], "数据能力": ["SQL"]})
    app = AppTest.from_file(str(PAGE), default_timeout=15)
    app.session_state["match_selection"] = json.dumps([saved_job, saved_candidate], sort_keys=True, ensure_ascii=False)
    app.session_state["match_result"] = report
    app.run()
    app.button[0].click().run()
    assert not app.exception
    assert app.session_state["interview_result"]["report"] == report


def test_navigation() -> None:
    app = AppTest.from_file(str(PAGE.parents[1] / "app.py"), default_timeout=15).run()
    app.switch_page("pages/04_面试助手.py").run()
    assert not app.exception and app.title[0].value == "面试助手"
