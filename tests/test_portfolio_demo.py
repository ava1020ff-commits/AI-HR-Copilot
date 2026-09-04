from services.portfolio_demo import build_demo


def test_demo_covers_three_evidence_levels() -> None:
    job, candidate, report = build_demo()
    assert "虚构" in job["job_title"] and "虚构" in candidate["candidate_name"]
    assert report["total_score"] == 57.5
    assert [d["criteria"][0]["attainment"] for d in report["dimensions"]] == [1, 0.5, 0]
    assert report["risks"] and report["questions_to_verify"]
    assert any("【仅技能自述】" in item for item in report["risks"])
    assert any("【材料未提及】" in item for item in report["risks"])
    assert all("信息矛盾" not in item for item in report["risks"])


def test_demo_records_are_independent() -> None:
    _, candidate, _ = build_demo()
    candidate["skills"].clear()
    assert build_demo()[1]["skills"] == ["RAG"]


def test_demo_explanation_renders() -> None:
    from pathlib import Path
    from streamlit.testing.v1 import AppTest

    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py")).run()
    app.button(key="portfolio_demo").click().run()
    assert not app.exception
    text = "\n".join(item.value for item in app.text)
    for label in ("岗位要求：", "权重：", "原文证据：", "证据类型：", "计分规则：", "待核实内容："):
        assert label in text
    assert "× 系数 0.5" in text and "× 系数 1" in text
    assert any("规则可复现不等于已经证明评分有效" in item.value for item in app.caption)
