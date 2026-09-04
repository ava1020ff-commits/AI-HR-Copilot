"""首页初始化冒烟测试。"""

from pathlib import Path

from streamlit.testing.v1 import AppTest


def test_homepage_renders_without_errors() -> None:
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    app = AppTest.from_file(str(app_path)).run(timeout=15)
    assert not app.exception
    assert app.title[0].value == "AI Recruitment Copilot"
    assert len(app.metric) == 4
    assert len(app.columns) == 7
    assert any("从岗位与简历出发" in item.value for item in app.markdown)
    assert not any("<style>" in item.value for item in app.markdown)
    assert any("<style>" in item.proto.body for item in app.get("html"))
    assert len(app.get("page_link")) == 11
    assert app.sidebar.get("page_link")[0].label == "招聘工作台"


def test_homepage_database_error_is_not_zero(monkeypatch) -> None:
    def unavailable():
        raise OSError("test-only database failure")

    monkeypatch.setattr("database.matching_records.list_jobs", unavailable)
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    app = AppTest.from_file(str(app_path)).run(timeout=15)
    assert not app.exception
    assert all(metric.value == "—" for metric in app.metric)
    assert "暂时无法读取" in app.warning[0].value


def test_placeholder_packages_import() -> None:
    import database
    import services

    assert database.__doc__
    assert services.__doc__
