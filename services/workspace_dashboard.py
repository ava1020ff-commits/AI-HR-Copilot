"""根据现有招聘记录计算首页指标、任务、日程与预警。"""

from datetime import datetime, timezone

SAVED_MINUTES = {"resume_screening": 3, "boss_message": 5, "interview_questions": 10, "candidate_analysis": 8, "jd_optimization": 10}


def _time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None


def calculate_workspace_dashboard(jobs: list[dict], candidates: list[dict], analytics: dict, usage: list[dict], *, now: datetime | None = None) -> dict:
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    job_names = {item["id"]: item["label"] for item in jobs}
    candidate_names = {item["id"]: item["label"] for item in candidates}
    reports = [item for item in analytics.get("reports", []) if item["job_id"] in job_names and item["candidate_id"] in candidate_names]
    report_candidate_ids = {item["candidate_id"] for item in reports}
    stages = [item for item in analytics.get("stages", []) if item["job_id"] in job_names and item["candidate_id"] in candidate_names]
    stage_pairs = {(item["job_id"], item["candidate_id"]): item for item in stages}

    pending_resume = [item for item in candidates if item["id"] not in report_candidate_ids]
    pending_contact = [item for item in stages if item["stage"] == "HR人工确认"]
    pending_interview = [item for item in stages if item["stage"] == "进入面试"]
    alerts = []
    for item in pending_contact:
        updated = _time(item.get("updated_at"))
        if updated and (now - updated).total_seconds() > 48 * 3600:
            alerts.append({"level": "red", "title": f"{candidate_names[item['candidate_id']]} · {job_names[item['job_id']]}", "detail": "已超过 48 小时未跟进", "action": "立即沟通", "path": "pages/08_BOSS沟通话术.py"})
    for item in stages:
        updated = _time(item.get("updated_at"))
        if item["stage"] == "Offer" and updated and (now - updated).total_seconds() > 3 * 86400:
            alerts.append({"level": "red", "title": f"{candidate_names[item['candidate_id']]} · {job_names[item['job_id']]}", "detail": "Offer 已记录超过 3 天，反馈状态待确认", "action": "查看分析", "path": "pages/05_招聘分析.py"})
    for job in jobs:
        related = [_time(item.get("updated_at")) for item in reports if item["job_id"] == job["id"]]
        related = [value for value in related if value]
        baseline = max(related) if related else _time(job.get("created_at"))
        if baseline and (now - baseline).total_seconds() > 7 * 86400:
            alerts.append({"level": "yellow", "title": job["label"], "detail": "连续 7 天没有新增候选人匹配记录", "action": "查看岗位", "path": "pages/07_已保存岗位.py"})

    tasks = []
    for candidate in pending_resume:
        tasks.append({"status": "待处理", "type": "简历筛选", "tone": "blue", "job": "待选择岗位", "summary": f"候选人：{candidate['label']}", "state": "新简历待筛选", "next": "完成人岗匹配", "owner": "我", "due": "待安排", "action": "AI 筛选", "path": "pages/03_智能匹配.py"})
    for item in pending_contact:
        tasks.append({"status": "待处理", "type": "候选人沟通", "tone": "orange", "job": job_names[item["job_id"]], "summary": f"候选人：{candidate_names[item['candidate_id']]}", "state": "HR 已确认，待首次沟通", "next": "发送 BOSS 初次沟通", "owner": "我", "due": "尽快处理", "action": "生成沟通话术", "path": "pages/08_BOSS沟通话术.py"})
    for item in pending_interview:
        tasks.append({"status": "进行中", "type": "面试准备", "tone": "purple", "job": job_names[item["job_id"]], "summary": f"候选人：{candidate_names[item['candidate_id']]}", "state": "已进入面试", "next": "准备结构化面试题", "owner": "我", "due": "待安排", "action": "生成面试题", "path": "pages/04_面试助手.py"})
    for item in stages:
        if item["stage"] == "Offer":
            tasks.append({"status": "进行中", "type": "Offer", "tone": "green", "job": job_names[item["job_id"]], "summary": f"候选人：{candidate_names[item['candidate_id']]}", "state": "Offer 阶段", "next": "确认候选人反馈", "owner": "我", "due": "待确认", "action": "查看详情", "path": "pages/05_招聘分析.py"})

    today_usage = [item for item in usage if (_time(item.get("created_at")) or datetime.min.replace(tzinfo=timezone.utc)).date() == now.date()]
    counts = {key: sum(item["action"] == key for item in today_usage) for key in SAVED_MINUTES}
    saved_minutes = sum(counts[key] * minutes for key, minutes in SAVED_MINUTES.items())
    today_candidates = sum((_time(item.get("confirmed_at")) or datetime.min.replace(tzinfo=timezone.utc)).date() == now.date() for item in candidates)
    return {
        "metrics": (
            {"label": "待筛选", "value": len(pending_resume), "detail": f"{today_candidates} 份今日新增", "tone": "blue"},
            {"label": "待沟通", "value": len(pending_contact), "detail": f"{sum(1 for a in alerts if '48 小时' in a['detail'])} 人超过 48h 未跟进", "tone": "orange"},
            {"label": "待面试", "value": len(pending_interview), "detail": "今日面试暂无排期数据", "tone": "purple"},
            {"label": "招聘预警", "value": len(alerts), "detail": "需要及时处理" if alerts else "当前无预警", "tone": "red"},
        ),
        "ai_usage": (("AI 筛选简历", f"{counts['resume_screening']} 份"), ("生成候选人沟通话术", f"{counts['boss_message']} 次"), ("生成面试题", f"{counts['interview_questions']} 份"), ("完成候选人分析", f"{counts['candidate_analysis']} 人"), ("预计节省招聘时间", f"{saved_minutes / 60:.1f} 小时")),
        "tasks": tuple(tasks), "schedule": (), "alerts": tuple(alerts), "active_jobs": len(jobs),
    }
