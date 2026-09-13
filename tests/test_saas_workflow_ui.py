"""Task navigation and truthful states, using only isolated synthetic records."""

from pathlib import Path
import sqlite3

import pytest
from streamlit.testing.v1 import AppTest

from services.ui import render_status


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def isolated(monkeypatch, tmp_path):
    monkeypatch.setenv("JD_DATABASE_PATH", str(tmp_path / "test.sqlite3"))
    monkeypatch.setenv("RESUME_DATABASE_PATH", str(tmp_path / "test.sqlite3"))
    monkeypatch.setenv("LLM_API_KEY", "")


def open_page(name: str) -> AppTest:
    return AppTest.from_file(str(ROOT / "app.py"), default_timeout=15).run().switch_page("pages/" + name).run()


def test_candidate_library_precedes_import_workflow() -> None:
    app = open_page("02_候选人.py")
    assert not app.exception
    assert app.subheader[0].value == "人才库"
    assert app.expander[0].label == "导入候选人 / 解析与复核"
    assert not app.expander[0].proto.expanded


def test_job_search_keeps_details_in_scope(monkeypatch) -> None:
    records = [{"id": i, "job_title": title, "work_location": location, "salary_range": "",
                "result": {"hard_skills": [skill]}, "source_jd": "合成岗位说明", "mode": "local"}
               for i, title, location, skill in [(1, "合成研发岗", "北京", "Python"), (2, "合成分析岗", "上海", "SQL")]]
    monkeypatch.setattr("database.jobs.list_saved_jobs", lambda: records)
    app = open_page("07_已保存岗位.py")
    assert not app.exception
    assert len(app.dataframe[0].value) == 2
    assert not any(item.value == "招聘中" for item in app.caption)
    app.text_input(key="job_query").input("SQL").run()
    assert not app.exception and len(app.dataframe[0].value) == 1
    assert app.selectbox[0].value == 2
    assert app.text_input(key="edit_title_2").value == "合成分析岗"
    app.text_input(key="job_query").input("不存在").run()
    assert not app.exception and not app.dataframe
    assert any("没有符合条件" in item.value for item in app.info)


def test_job_read_failure_is_not_empty_state(monkeypatch) -> None:
    def fail() -> None:
        raise sqlite3.OperationalError("synthetic failure")
    monkeypatch.setattr("database.jobs.list_saved_jobs", fail)
    app = open_page("07_已保存岗位.py")
    assert not app.exception and app.error
    assert not any("暂无已保存岗位" in item.value for item in app.markdown)


def test_missing_schedule_is_not_reported_as_zero_tasks() -> None:
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=15).run()
    assert not app.exception
    markup = [item.value for item in app.markdown]
    assert any("未接入" in item and "hr-status" in item for item in markup)
    assert "**—**" in markup
    assert any("暂无待办" in item and "hr-status" in item for item in markup)


def test_status_label_is_escaped_and_tone_is_validated(monkeypatch) -> None:
    output = []
    monkeypatch.setattr("streamlit.markdown", lambda value, **kwargs: output.append(value))
    render_status("<b>label</b>")
    assert "&lt;b&gt;label&lt;/b&gt;" in output[0]
    with pytest.raises(ValueError):
        render_status("label", "unexpected")
