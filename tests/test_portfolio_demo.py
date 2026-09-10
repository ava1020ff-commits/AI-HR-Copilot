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


def test_demo_explanation_is_not_rendered_on_workspace_home(monkeypatch, tmp_path) -> None:
    from pathlib import Path
    from streamlit.testing.v1 import AppTest

    monkeypatch.setenv("JD_DATABASE_PATH", str(tmp_path / "empty.sqlite3"))
    monkeypatch.setenv("RESUME_DATABASE_PATH", str(tmp_path / "empty.sqlite3"))
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py")).run()
    assert not app.exception
    assert not any(getattr(item, "key", None) == "portfolio_demo" for item in app.button)
