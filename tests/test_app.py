"""首页初始化冒烟测试。"""

from pathlib import Path
import re

from streamlit.testing.v1 import AppTest


def test_homepage_renders_without_errors() -> None:
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    app = AppTest.from_file(str(app_path)).run(timeout=15)
    assert not app.exception
    assert app.title[0].value == "招聘工作台"
    assert len(app.metric) == 4
    assert len(app.columns) >= 8
    assert not any("从岗位与简历出发" in item.value for item in app.markdown)
    assert not any("AI 辅助分析 · HR 确认与决策" in item.value for item in app.caption)
    assert not any("<style>" in item.value for item in app.markdown)
    assert any("<style>" in item.proto.body for item in app.get("html"))
    assert len(app.get("page_link")) >= 17
    assert app.get("popover")[0].proto.popover.label == "菜单"
    assert any(item.label == "开始匹配 →" for item in app.get("page_link"))
    assert app.sidebar.get("page_link")[0].label == "▦  工作台"


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


def test_visual_system_contract() -> None:
    css = (Path(__file__).resolve().parents[1] / "services" / "theme.css").read_text(encoding="utf-8")
    assert "gradient" not in css.lower()
    assert "text-shadow" not in css.lower()
    assert "--hr-focus: #2563eb" in css and "--hr-on-dark: #2563eb" in css
    assert "--hr-radius: 12px" in css and "--hr-pill" not in css
    assert re.search(r"min-height:\s*48px", css)
    assert "overflow-x: hidden" in css and "overflow-x: auto" in css
    for declaration in re.findall(r"(?:margin|padding|gap)(?:-[a-z]+)?\s*:\s*([^;]+)", css):
        values = re.findall(r"(?<![-\d.])(\d+)px", declaration)
        assert all(int(value) in {0, 8, 16, 24, 32} for value in values), declaration
