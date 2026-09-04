"""JD 模块测试；不访问真实 API，数据库写入临时目录。"""

import copy
import json
import sqlite3
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import requests
from streamlit.testing.v1 import AppTest

from database.jobs import save_job
from services.jd_parser import JDParseError, LLMConfig, MOCK_JOB, parse_jd, validate_job

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


def test_invalid_result_not_saved(tmp_path) -> None:
    path = tmp_path / "invalid.sqlite3"
    with pytest.raises(JDParseError):
        save_job(JD, {}, "mock", path)
    assert not path.exists()


def test_page_mock_flow_and_rerun(tmp_path) -> None:
    app = AppTest.from_file(str(PAGE), default_timeout=15).run()
    assert not app.exception
    assert app.checkbox[0].value is True
    app.text_area[0].input(JD)
    app.button[0].click().run()
    assert not app.exception
    assert app.success and app.json and app.table
    app.run()
    assert app.success
    with sqlite3.connect(tmp_path / "jobs.sqlite3") as connection:
        assert connection.execute("SELECT COUNT(*) FROM jd_jobs").fetchone()[0] == 1
    app.text_area[0].input(" ")
    app.button[0].click().run()
    assert app.error
    assert not app.success


def test_page_save_failure(monkeypatch) -> None:
    monkeypatch.setattr("database.jobs.save_job", MagicMock(side_effect=sqlite3.OperationalError("locked")))
    app = AppTest.from_file(str(PAGE), default_timeout=15).run()
    app.text_area[0].input(JD)
    app.button[0].click().run()
    assert not app.exception
    assert "保存失败" in app.error[0].value
    assert not app.success


def test_page_requires_consent_in_real_mode(monkeypatch) -> None:
    monkeypatch.setenv("LLM_API_KEY", "test-only-key")
    monkeypatch.setenv("LLM_MODEL", "test-model")
    app = AppTest.from_file(str(PAGE), default_timeout=15).run()
    app.text_area[0].input(JD)
    app.button[0].click().run()
    assert "授权" in app.error[0].value
    assert not app.exception


def test_homepage_navigation_to_jd() -> None:
    app = AppTest.from_file(str(PAGE.parents[1] / "app.py"), default_timeout=15).run()
    app.switch_page("pages/01_岗位管理.py").run()
    assert not app.exception
    assert app.title[0].value == "JD 解析"
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
