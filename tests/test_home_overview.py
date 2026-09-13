from datetime import datetime, timezone

from services.workspace_dashboard import calculate_recruitment_overview


NOW = datetime(2026, 9, 13, 17, tzinfo=timezone.utc)  # Sept 14 in Beijing.


def test_today_uses_beijing_midnight_and_missing_dates() -> None:
    candidates = [
        {"id": 1, "label": "A", "confirmed_at": "2026-09-13T15:59:59Z"},
        {"id": 2, "label": "B", "confirmed_at": "2026-09-13T16:00:00Z"},
        {"id": 3, "label": "C", "confirmed_at": "invalid"},
    ]
    result = calculate_recruitment_overview([], candidates, {}, now=NOW)
    assert [item["value"] for item in result["metrics"]] == [3, 1, 0, 0]
    assert result["actions"][1]["available"] is False
    assert result["actions"][1]["value"] == 0


def test_people_are_deduplicated_and_progress_is_scoped() -> None:
    jobs = [{"id": 1, "label": "岗位A"}, {"id": 2, "label": "岗位B"}]
    candidates = [{"id": 1, "label": "候选人A"}, {"id": 2, "label": "未关联"}]
    analytics = {"reports": [{"job_id": 1, "candidate_id": 1}, {"job_id": 2, "candidate_id": 1}],
                 "stages": [{"job_id": 1, "candidate_id": 1, "stage": "进入面试"},
                            {"job_id": 2, "candidate_id": 1, "stage": "Offer"},
                            {"job_id": 99, "candidate_id": 1, "stage": "Offer"},
                            {"job_id": 1, "candidate_id": 99, "stage": "Offer"}]}
    result = calculate_recruitment_overview(jobs, candidates, analytics, now=NOW)
    assert [item["value"] for item in result["metrics"]] == [2, 0, 1, 1]
    assert [item["value"] for item in result["actions"]] == [1, 0, 0, 1]
    assert result["job_progress"][0]["面试中"] == 1
    assert result["job_progress"][1]["Offer中"] == 1
    scoped = calculate_recruitment_overview(jobs, candidates, analytics, selected_job=2, now=NOW)
    assert [item["value"] for item in scoped["metrics"]] == [1, 0, 0, 1]
    assert len(scoped["job_progress"]) == 1
    assert scoped["actions"][0]["value"] == 0


def test_empty_and_stale_job_filter_do_not_leak_candidates() -> None:
    for selected in (None, 99):
        result = calculate_recruitment_overview([], [], {}, selected_job=selected, now=NOW)
        assert [item["value"] for item in result["metrics"]] == [0, 0, 0, 0]
        assert all(not item["rows"] for item in result["actions"])
        assert not result["job_progress"]
    result = calculate_recruitment_overview([], [{"id": 1, "label": "A"}], {}, selected_job=99, now=NOW)
    assert result["metrics"][0]["value"] == 0
