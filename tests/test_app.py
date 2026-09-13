"""首页初始化冒烟测试。"""

from pathlib import Path
import re

from streamlit.testing.v1 import AppTest


def test_homepage_renders_without_errors() -> None:
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    app = AppTest.from_file(str(app_path)).run(timeout=15)
    assert not app.exception
    assert app.title[0].value == "招聘工作台"
    assert len(app.text_input) == 1
    assert app.text_input[0].placeholder == "搜索候选人或岗位"
    assert len(app.columns) >= 2
    assert not any("从岗位与简历出发" in item.value for item in app.markdown)
    assert not any("AI 辅助分析 · HR 确认与决策" in item.value for item in app.caption)
    assert not any("<style>" in item.value for item in app.markdown)
    assert any("<style>" in item.proto.body for item in app.get("html"))
    assert len(app.get("page_link")) >= 10
    assert app.get("popover")[0].proto.popover.label == "菜单"
    assert any(item.label == "BOSS沟通话术" for item in app.get("page_link"))
    assert [item.value for item in app.subheader] == ["需要我处理", "招聘进展", "AI 助手"]
    assert app.selectbox[0].label == "岗位筛选"
    assert app.selectbox[0].value == "all"
    assert any("北京时间" in item.value for item in app.caption)
    assert not any("本月人力运营" in item.value for item in app.subheader)
    assert not any("员工花名册、绩效和人力成本数据尚未接入" in item.value for item in app.info)
    assert not any("待办事项" in item.value for item in app.subheader)
    assert not any("快捷入口" in item.value for item in app.subheader)
    assert not any("最近候选人" in item.value for item in app.subheader)
    assert app.sidebar.get("page_link")[0].label == "▦  首页"
    sidebar_captions = [item.value for item in app.sidebar.caption]
    assert "概览" in sidebar_captions
    assert "招聘管理" in sidebar_captions
    assert "AI 招聘" in sidebar_captions
    assert "数据分析" in sidebar_captions
    assert "人力分析" in sidebar_captions
    sidebar_links = [item.label for item in app.sidebar.get("page_link")]
    assert "◇  组织与岗位" not in sidebar_links
    assert "◎  绩效管理" not in sidebar_links
    assert "△  人才发展" not in sidebar_links


def test_homepage_search_filters_tasks() -> None:
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    app = AppTest.from_file(str(app_path)).run(timeout=15)
    app.text_input[0].input("不存在的任务").run(timeout=15)
    assert not app.exception
    assert any("没有找到匹配的待办" in item.value for item in app.caption)


def test_placeholder_packages_import() -> None:
    import database
    import services

    assert database.__doc__
    assert services.__doc__


def test_visual_system_contract() -> None:
    css = (Path(__file__).resolve().parents[1] / "services" / "theme.css").read_text(encoding="utf-8")
    assert "gradient" not in css.lower()
    assert "text-shadow" not in css.lower()
    from services.design_system import TOKENS
    assert TOKENS["radius"] == "8px"
    assert TOKENS["control-height"] == "44px"
    assert "overflow-x: hidden" in css and "overflow-x: auto" in css
    referenced = set(re.findall(r"var\(--hr-([\w-]+)\)", css))
    assert referenced <= TOKENS.keys()
