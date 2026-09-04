"""候选人检索使用虚构数据，不读取真实数据库。"""

from pathlib import Path

from streamlit.testing.v1 import AppTest

from services.candidate_search import filter_candidates


def records() -> list[dict]:
    return [
        {"id": 1, "label": "测试甲", "mode": "local", "data": {
            "candidate_name": "测试甲", "education": ["本科"], "skills": ["Python"],
            "projects": ["搜索项目"], "gender": "不应检索的字段"}},
        {"id": 2, "label": "测试乙", "mode": "local", "data": {
            "candidate_name": "测试乙", "education": [], "skills": ["SQL"]}},
    ]


def test_search_and_combined_filters() -> None:
    items = records()
    assert filter_candidates(items) == items
    assert filter_candidates(items, " python 搜索 ", "本科", "Python") == items[:1]
    assert filter_candidates(items, "测试乙") == items[1:]
    assert filter_candidates(items, "2") == items[1:]
    assert filter_candidates(items, "不应检索的字段") == []
    assert filter_candidates(items, skill="SQL", education="本科") == []
    assert filter_candidates([], "测试") == []


def test_page_search_reset_and_empty_results(monkeypatch) -> None:
    monkeypatch.setattr("database.matching_records.list_candidates", records)
    monkeypatch.setenv("LLM_API_KEY", "")
    page = Path(__file__).resolve().parents[1] / "pages" / "02_候选人.py"
    app = AppTest.from_file(str(page.parents[1] / "app.py")).run(timeout=15).switch_page("pages/" + page.name).run(timeout=15)
    assert not app.exception
    assert len(app.dataframe[0].value) == 2
    app.text_input(key="candidate_query").input("python").run()
    assert len(app.dataframe[0].value) == 1
    app.selectbox(key="candidate_skill").select("SQL").run()
    assert not app.dataframe
    assert any("没有符合条件" in item.value for item in app.info)
    next(button for button in app.button if button.label == "清空筛选").click().run()
    assert not app.exception
    assert len(app.dataframe[0].value) == 2
