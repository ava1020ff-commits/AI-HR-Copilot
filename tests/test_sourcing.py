from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from services.sourcing import boolean_search, parse_import, search_terms


@pytest.fixture(autouse=True)
def isolated_database(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("JD_DATABASE_PATH", str(tmp_path / "jobs.sqlite3"))


def test_search_terms_are_deduplicated() -> None:
    assert search_terms({"job_title": "后端工程师", "hard_skills": ["Python", "Python"], "soft_skills": ["协作"]}) == ["后端工程师", "Python", "协作"]


def test_boolean_search_is_grouped_and_readable() -> None:
    assert boolean_search(["客服组长", "团队管理", "数据分析"]) == (
        '"客服组长"\nAND (\n  "团队管理"\n  OR "数据分析"\n)'
    )


def test_import_one_authorized_shape() -> None:
    content = "candidate_name,education,work_experience,internships,projects,skills,certificates,source_reference\n虚构甲,本科,负责接口开发,,项目A,Python|SQL,,BOSS-REF-001\n".encode()
    candidate, source = parse_import(content)
    assert candidate["skills"] == ["Python", "SQL"] and source == "BOSS-REF-001"


@pytest.mark.parametrize("content", [b"", b"wrong\nvalue\n"])
def test_invalid_import_rejected(content: bytes) -> None:
    with pytest.raises(ValueError):
        parse_import(content)


def test_empty_page_requires_job() -> None:
    page = Path(__file__).resolve().parents[1] / "pages" / "06_候选人寻访.py"
    app = AppTest.from_file(str(page.parents[1] / "app.py"), default_timeout=15).run().switch_page("pages/" + page.name).run()
    assert not app.exception and any("暂无可寻访岗位" in item.value for item in app.markdown)
