"""首页真实数据统计测试。"""

from datetime import datetime, timedelta, timezone

from database.activity import list_ai_usage, record_ai_usage
from services.workspace_dashboard import calculate_workspace_dashboard


NOW = datetime(2026, 9, 11, 8, tzinfo=timezone.utc)


def test_empty_dashboard_uses_zero_not_demo_data() -> None:
    result = calculate_workspace_dashboard([], [], {"reports": [], "stages": []}, [], now=NOW)
    assert [item["value"] for item in result["metrics"]] == [0, 0, 0, 0]
    assert result["tasks"] == () and result["schedule"] == () and result["alerts"] == ()
    assert result["ai_usage"][-1][1] == "0.0 小时"


def test_real_records_drive_metrics_tasks_alerts_and_usage() -> None:
    old = (NOW - timedelta(days=8)).isoformat()
    today = NOW.isoformat()
    jobs = [{"id": 1, "label": "产品经理", "data": {}, "mode": "local", "created_at": old}]
    candidates = [
        {"id": 10, "label": "新候选人", "data": {}, "mode": "local", "confirmed_at": today},
        {"id": 11, "label": "待沟通人", "data": {}, "mode": "local", "confirmed_at": old},
        {"id": 12, "label": "待面试人", "data": {}, "mode": "local", "confirmed_at": old},
    ]
    analytics = {
        "reports": [
            {"job_id": 1, "candidate_id": 11, "total_score": 80, "report": {}, "updated_at": old},
            {"job_id": 1, "candidate_id": 12, "total_score": 80, "report": {}, "updated_at": today},
        ],
        "stages": [
            {"job_id": 1, "candidate_id": 11, "stage": "HR人工确认", "updated_at": old},
            {"job_id": 1, "candidate_id": 12, "stage": "进入面试", "updated_at": today},
        ],
    }
    usage = [{"action": "boss_message", "job_id": 1, "candidate_id": 11, "created_at": today}]
    result = calculate_workspace_dashboard(jobs, candidates, analytics, usage, now=NOW)
    assert [item["value"] for item in result["metrics"][:3]] == [1, 1, 1]
    assert result["metrics"][3]["value"] == len(result["alerts"])
    assert {task["type"] for task in result["tasks"]} == {"简历筛选", "候选人沟通", "面试准备"}
    assert result["ai_usage"][1][1] == "1 次"
    assert result["ai_usage"][-1][1] == "0.1 小时"


def test_ai_usage_is_persisted_in_sqlite(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("JD_DATABASE_PATH", str(tmp_path / "activity.sqlite3"))
    record_ai_usage("boss_message", job_id=3, candidate_id=7)
    saved = list_ai_usage()
    assert saved[0]["action"] == "boss_message"
    assert saved[0]["job_id"] == 3 and saved[0]["candidate_id"] == 7
