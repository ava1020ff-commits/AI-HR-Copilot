"""Homepage presentation states; no production data or API calls."""

from pathlib import Path
import re
import sqlite3

import pytest
from streamlit.testing.v1 import AppTest

from services.design_system import TOKENS


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def isolated(monkeypatch, tmp_path):
    monkeypatch.setenv("JD_DATABASE_PATH", str(tmp_path / "test.sqlite3"))
    monkeypatch.setenv("RESUME_DATABASE_PATH", str(tmp_path / "test.sqlite3"))


def test_empty_home_keeps_tools_and_disables_only_unavailable_filter() -> None:
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=15).run()
    assert not app.exception
    assert app.selectbox(key="workspace_job").disabled
    labels = {item.label for item in app.get("page_link")}
    assert {"去筛选", "面试准备", "去跟进", "查看 Offer", "JD分析", "简历匹配", "面试题生成", "BOSS沟通话术"} <= labels
    assert not any(item.disabled for item in app.get("page_link"))
    assert [item.value for item in app.markdown if item.value.startswith("## ")] == ["## 0"] * 4
    assert {item.label for item in app.expander} >= {"查看待办明细", "统计口径与数据说明"}


def test_read_error_can_retry_without_showing_false_zero(monkeypatch) -> None:
    state = {"fail": True}

    def read_jobs() -> list[dict]:
        if state["fail"]:
            raise sqlite3.OperationalError("isolated test failure")
        return []

    monkeypatch.setattr("database.matching_records.list_jobs", read_jobs)
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=15).run()
    assert not app.exception and app.error
    assert not any(item.value.startswith("## ") for item in app.markdown)
    state["fail"] = False
    app.button(key="workspace_retry").click().run()
    assert not app.exception and not app.error
    assert [item.value for item in app.markdown if item.value.startswith("## ")] == ["## 0"] * 4


def test_filter_change_gives_confirmation_and_keeps_selection(monkeypatch) -> None:
    monkeypatch.setattr("database.matching_records.list_jobs", lambda: [{"id": 1, "label": "合成岗位"}])
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=15).run()
    assert not app.selectbox(key="workspace_job").disabled
    app.selectbox(key="workspace_job").select(1).run()
    assert not app.exception and app.selectbox(key="workspace_job").value == 1
    assert app.get("toast")[0].proto.body == "岗位筛选已更新"


def test_home_styles_are_scoped_and_reuse_existing_tokens() -> None:
    css = (ROOT / "services/workspace.css").read_text(encoding="utf-8")
    assert not re.search(r"#[0-9a-fA-F]{3,8}\b", css)
    assert set(re.findall(r"var\(--hr-([\w-]+)\)", css)) <= TOKENS.keys()
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    for selector in re.findall(r"([^{}]+)\{", css):
        if not selector.strip().startswith("@"):
            assert selector.strip().startswith(".st-key-recruitment_home"), selector
