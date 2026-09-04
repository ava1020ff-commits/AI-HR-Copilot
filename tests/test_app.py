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
    assert "一体化智能工作台" in app.markdown[1].value


def test_placeholder_packages_import() -> None:
    import database
    import services

    assert database.__doc__
    assert services.__doc__
