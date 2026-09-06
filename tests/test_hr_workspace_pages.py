"""新增人力工作台模块页面冒烟测试。"""

from pathlib import Path

from streamlit.testing.v1 import AppTest


def test_people_movement_page_renders() -> None:
    root = Path(__file__).resolve().parents[1]
    app = AppTest.from_file(str(root / "app.py")).run(timeout=15)
    app.switch_page("pages/11_人员异动.py").run(timeout=15)

    assert not app.exception
    assert app.title[0].value == "人员异动"
    assert len(app.metric) == 4
    assert len(app.dataframe) == 0
    assert any(item.label == "查看异动跟进流程" for item in app.expander)


def test_people_cost_page_renders() -> None:
    root = Path(__file__).resolve().parents[1]
    app = AppTest.from_file(str(root / "app.py")).run(timeout=15)
    app.switch_page("pages/12_人力成本.py").run(timeout=15)

    assert not app.exception
    assert app.title[0].value == "人力成本"
    assert len(app.metric) == 4
    assert len(app.dataframe) == 1
    assert any(item.label == "核算设置" for item in app.expander)
    assert any(item.label == "查看计算流程与规则" for item in app.expander)
    assert any(item.label == "查看指标说明" for item in app.expander)
