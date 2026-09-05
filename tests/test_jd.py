"""JD 模块测试；不访问真实 API，数据库写入临时目录。"""

import copy
import json
import sqlite3
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import requests
from streamlit.testing.v1 import AppTest

from database.jobs import list_saved_jobs, save_job, update_job
from services.jd_parser import JDParseError, LLMConfig, MOCK_JOB, parse_jd, parse_jd_local, validate_job

PAGE = Path(__file__).resolve().parents[1] / "pages" / "01_岗位管理.py"
JD = "Python 后端工程师，本科，3 年经验，熟悉 SQL，良好的沟通能力。"


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch, tmp_path):
    for key in ("LLM_API_KEY", "LLM_MODEL", "LLM_BASE_URL"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("JD_DATABASE_PATH", str(tmp_path / "jobs.sqlite3"))
    monkeypatch.setattr("services.jd_parser.requests.post", MagicMock(side_effect=AssertionError("禁止真实网络请求")))


def test_mock_is_default_and_independent() -> None:
    result = parse_jd(JD)
    assert result == MOCK_JOB
    result["hard_skills"].clear()
    assert parse_jd(JD)["hard_skills"]


def test_local_parser_uses_pasted_jd() -> None:
    jd = """工作职责：负责客服团队管理、流程优化与数据分析。
任职要求：大专及以上，三年以上客服团队管理经验；跨团队协作能力强。
熟悉 B 站内容生态者优先。"""
    result = parse_jd_local(jd, "客服运营主管")
    assert result["job_title"] == "客服运营主管"
    assert result["education"] == "大专"
    assert "三年" in result["experience"]
    assert "团队管理" in result["hard_skills"]
    assert "数据分析" in result["hard_skills"]
    assert "跨团队协作" in result["soft_skills"]
    assert sum(item["weight"] for item in result["competency_model"]) == 100
    assert result != MOCK_JOB


def test_local_parser_requires_recognisable_content() -> None:
    with pytest.raises(JDParseError, match="未识别"):
        parse_jd_local("这里没有明确的职业要求", "测试岗位")


@pytest.mark.parametrize("jd", ["", "   ", "a" * 20001], ids=["empty", "whitespace", "too_long"])
def test_invalid_input(jd: str) -> None:
    with pytest.raises(JDParseError):
        parse_jd(jd)


@pytest.mark.parametrize("field,value", [
    ("job_title", ""), ("hard_skills", "Python"), ("soft_skills", [1]),
    ("competency_model", {}),
])
def test_invalid_fields(field: str, value: object) -> None:
    result = copy.deepcopy(MOCK_JOB)
    result[field] = value
    with pytest.raises(JDParseError):
        validate_job(result)


@pytest.mark.parametrize("weight", [-1, 101, True, float("nan"), float("inf"), "50", 49])
def test_invalid_weights(weight: object) -> None:
    result = copy.deepcopy(MOCK_JOB)
    result["competency_model"][0]["weight"] = weight
    with pytest.raises(JDParseError):
        validate_job(result)


def test_missing_field_and_duplicate_dimension() -> None:
    result = copy.deepcopy(MOCK_JOB)
    del result["education"]
    with pytest.raises(JDParseError):
        validate_job(result)
    result = copy.deepcopy(MOCK_JOB)
    result["competency_model"][1]["dimension"] = result["competency_model"][0]["dimension"]
    with pytest.raises(JDParseError):
        validate_job(result)


def test_empty_competency_model_is_valid() -> None:
    result = copy.deepcopy(MOCK_JOB)
    result["competency_model"] = []
    assert validate_job(result)["competency_model"] == []


def mock_response(monkeypatch, content: str, status: int = 200, finish: str = "stop") -> MagicMock:
    response = MagicMock()
    response.status_code = status
    response.json.return_value = {"choices": [{"finish_reason": finish, "message": {"content": content}}]}
    post = MagicMock(return_value=response)
    monkeypatch.setattr("services.jd_parser.requests.post", post)
    return post


def test_real_request_contract(monkeypatch) -> None:
    post = mock_response(monkeypatch, json.dumps(MOCK_JOB))
    config = LLMConfig("test-only-key", "https://example.invalid/v1", "test-model")
    assert parse_jd(JD, config, False) == MOCK_JOB
    assert post.call_args.args[0] == "https://example.invalid/v1/chat/completions"
    assert post.call_args.kwargs["json"]["response_format"] == {"type": "json_object"}
    assert post.call_args.kwargs["json"]["messages"][1]["content"] == JD
    assert post.call_args.kwargs["allow_redirects"] is False


@pytest.mark.parametrize("content,status,finish", [("not json", 200, "stop"), ("{}", 200, "stop"), ("{}", 401, "stop"), ("{}", 429, "stop"), ("{}", 200, "length")])
def test_api_errors(monkeypatch, content: str, status: int, finish: str) -> None:
    mock_response(monkeypatch, content, status, finish)
    with pytest.raises(JDParseError):
        parse_jd(JD, LLMConfig("test-only-key", "https://example.invalid/v1", "test-model"), False)


def test_timeout_and_missing_config(monkeypatch) -> None:
    with pytest.raises(JDParseError):
        parse_jd(JD, LLMConfig(), False)
    monkeypatch.setattr("services.jd_parser.requests.post", MagicMock(side_effect=requests.Timeout("secret")))
    with pytest.raises(JDParseError, match="超时") as error:
        parse_jd(JD, LLMConfig("test-only-key", "https://example.invalid/v1", "test-model"), False)
    assert "secret" not in str(error.value)


def test_sqlite_persists_and_deduplicates(tmp_path) -> None:
    path = tmp_path / "saved.sqlite3"
    job_id = save_job(JD, MOCK_JOB, "mock", path)
    assert save_job(JD, MOCK_JOB, "mock", path) == job_id
    assert save_job(JD, MOCK_JOB, "llm", path) != job_id
    with sqlite3.connect(path) as connection:
        row = connection.execute("SELECT source_jd, parsed_json, mode, created_at FROM jd_jobs WHERE id=?", (job_id,)).fetchone()
        assert row[0] == JD
        assert json.loads(row[1]) == MOCK_JOB
        assert row[2] == "mock"
        assert row[3].endswith("Z")
        assert connection.execute("SELECT COUNT(*) FROM jd_jobs").fetchone()[0] == 2


def test_sqlite_accepts_local_mode_and_migrates_legacy_table(tmp_path) -> None:
    path = tmp_path / "legacy.sqlite3"
    legacy_id = save_job(JD, MOCK_JOB, "mock", path)
    with sqlite3.connect(path) as connection:
        connection.execute("ALTER TABLE jd_jobs RENAME TO current_jobs")
        connection.execute("""CREATE TABLE jd_jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT, job_title TEXT NOT NULL,
            source_jd TEXT NOT NULL, parsed_json TEXT NOT NULL,
            mode TEXT NOT NULL CHECK (mode IN ('mock', 'llm')),
            fingerprint TEXT NOT NULL UNIQUE, created_at TEXT NOT NULL)""")
        connection.execute(
            "INSERT INTO jd_jobs SELECT id, job_title, source_jd, parsed_json, mode, fingerprint, created_at FROM current_jobs"
        )
        connection.execute("DROP TABLE current_jobs")
    local = parse_jd_local(JD, "Python 后端工程师")
    local_id = save_job(JD, local, "local", path)
    assert local_id != legacy_id
    with sqlite3.connect(path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM jd_jobs").fetchone()[0] == 2
        assert connection.execute("SELECT mode FROM jd_jobs WHERE id=?", (local_id,)).fetchone()[0] == "local"


def test_saved_job_can_be_edited_without_changing_id(tmp_path) -> None:
    path = tmp_path / "editable.sqlite3"
    job_id = save_job(JD, MOCK_JOB, "mock", path)
    edited_jd = "客服运营主管：负责团队管理、流程优化和数据分析；本科，三年以上经验。"
    edited = parse_jd_local(edited_jd, "客服运营主管")
    assert update_job(
        job_id, edited_jd, edited, "local", path,
        work_location="上海", salary_range="15K–25K · 14薪",
    ) == job_id
    records = list_saved_jobs(path)
    assert len(records) == 1
    assert records[0]["id"] == job_id
    assert records[0]["job_title"] == "客服运营主管"
    assert records[0]["source_jd"] == edited_jd
    assert records[0]["mode"] == "local"
    assert records[0]["work_location"] == "上海"
    assert records[0]["salary_range"] == "15K–25K · 14薪"


def test_legacy_saved_jobs_are_readable_without_metadata_columns(tmp_path) -> None:
    path = tmp_path / "legacy-readable.sqlite3"
    payload = json.dumps(MOCK_JOB, ensure_ascii=False, sort_keys=True)
    with sqlite3.connect(path) as connection:
        connection.execute("""CREATE TABLE jd_jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT, job_title TEXT NOT NULL,
            source_jd TEXT NOT NULL, parsed_json TEXT NOT NULL,
            mode TEXT NOT NULL, fingerprint TEXT NOT NULL UNIQUE,
            created_at TEXT NOT NULL)""")
        connection.execute(
            "INSERT INTO jd_jobs VALUES (1, ?, ?, ?, 'mock', 'legacy', '2026-01-01T00:00:00Z')",
            (MOCK_JOB["job_title"], JD, payload),
        )
    records = list_saved_jobs(path)
    assert records[0]["job_title"] == MOCK_JOB["job_title"]
    assert records[0]["work_location"] == ""
    assert records[0]["salary_range"] == ""


def test_updating_unknown_job_is_rejected(tmp_path) -> None:
    path = tmp_path / "editable.sqlite3"
    save_job(JD, MOCK_JOB, "mock", path)
    with pytest.raises(ValueError, match="不存在"):
        update_job(999, JD, MOCK_JOB, "mock", path)


def test_invalid_result_not_saved(tmp_path) -> None:
    path = tmp_path / "invalid.sqlite3"
    with pytest.raises(JDParseError):
        save_job(JD, {}, "mock", path)
    assert not path.exists()


def test_page_local_flow_and_rerun(tmp_path) -> None:
    app = AppTest.from_file(str(PAGE.parents[1] / "app.py"), default_timeout=15).run().switch_page("pages/" + PAGE.name).run()
    assert not app.exception
    assert app.radio[0].value == "本地解析"
    app.text_area[0].input(JD)
    app.text_input[0].input("Python 后端工程师")
    next(button for button in app.button if button.label == "✦ AI 解析并保存岗位").click().run()
    assert not app.exception
    assert app.success and app.json and app.dataframe
    app.run()
    assert app.success
    with sqlite3.connect(tmp_path / "jobs.sqlite3") as connection:
        assert connection.execute("SELECT COUNT(*) FROM jd_jobs").fetchone()[0] == 1
    app.text_area[0].input(" ")
    next(button for button in app.button if button.label == "✦ AI 解析并保存岗位").click().run()
    assert app.error
    assert not app.success


def test_page_loads_saved_job_for_editing(tmp_path) -> None:
    save_job(JD, MOCK_JOB, "mock", tmp_path / "jobs.sqlite3")
    saved_page = PAGE.with_name("07_已保存岗位.py")
    app = AppTest.from_file(str(PAGE.parents[1] / "app.py"), default_timeout=15).run().switch_page("pages/" + saved_page.name).run()
    assert not app.exception
    assert app.text_area[0].value == JD
    assert app.text_input[0].value == MOCK_JOB["job_title"]
    assert any(button.label == "重新解析并更新" for button in app.button)


def test_page_save_failure(monkeypatch) -> None:
    monkeypatch.setattr("database.jobs.save_job", MagicMock(side_effect=sqlite3.OperationalError("locked")))
    app = AppTest.from_file(str(PAGE.parents[1] / "app.py"), default_timeout=15).run().switch_page("pages/" + PAGE.name).run()
    app.text_area[0].input(JD)
    app.button[0].click().run()
    assert not app.exception
    assert "保存失败" in app.error[0].value
    assert not app.success


def test_page_requires_consent_in_real_mode(monkeypatch) -> None:
    monkeypatch.setenv("LLM_API_KEY", "test-only-key")
    monkeypatch.setenv("LLM_MODEL", "test-model")
    app = AppTest.from_file(str(PAGE.parents[1] / "app.py"), default_timeout=15).run().switch_page("pages/" + PAGE.name).run()
    app.radio[0].set_value("智能解析").run()
    app.text_area[0].input(JD)
    app.button[0].click().run()
    assert "授权" in app.error[0].value
    assert not app.exception


def test_homepage_navigation_to_jd() -> None:
    app = AppTest.from_file(str(PAGE.parents[1] / "app.py"), default_timeout=15).run()
    app.switch_page("pages/01_岗位管理.py").run()
    assert not app.exception
    assert app.title[0].value == "创建岗位"
    app.text_area[0].input(JD)
    app.button[0].click().run()
    assert not app.exception
    assert app.success


@pytest.mark.parametrize("envelope", [{"choices": [None]}, {"choices": []}, {"choices": [{"finish_reason": "stop", "message": None}]}])
def test_invalid_response_envelope(monkeypatch, envelope: dict) -> None:
    post = mock_response(monkeypatch, "{}")
    post.return_value.json.return_value = envelope
    with pytest.raises(JDParseError):
        parse_jd(JD, LLMConfig("test-only-key", "https://example.invalid/v1", "test-model"), False)


def test_bad_url_is_safe_error() -> None:
    with pytest.raises(JDParseError):
        parse_jd(JD, LLMConfig("test-only-key", "https://[invalid", "test-model"), False)
