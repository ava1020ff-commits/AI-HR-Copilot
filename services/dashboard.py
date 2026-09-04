"""Recruitment Dashboard 纯统计逻辑。"""

from collections import defaultdict

HIGH_MATCH_THRESHOLD = 80.0
FUNNEL_STAGES = ("收到简历", "AI辅助筛选", "HR人工确认", "进入面试", "Offer")
STAGE_RANK = {"HR人工确认": 2, "进入面试": 3, "Offer": 4}


def dashboard_metrics(jobs: list[dict], candidates: list[dict], analytics: dict) -> dict:
    reports = analytics["reports"]
    stages = analytics["stages"]
    job_ids = {item["id"] for item in jobs}
    candidate_ids = {item["id"] for item in candidates}
    valid_reports = [item for item in reports if item["job_id"] in job_ids and item["candidate_id"] in candidate_ids]
    candidate_best = {}
    job_scores = defaultdict(list)
    dimension_scores = defaultdict(list)
    for item in valid_reports:
        score = float(item["total_score"])
        if not 0 <= score <= 100:
            raise ValueError("匹配分必须位于 0 到 100。")
        candidate_best[item["candidate_id"]] = max(score, candidate_best.get(item["candidate_id"], 0))
        job_scores[item["job_id"]].append(score)
        for dimension in item["report"].get("dimensions", []):
            maximum = float(dimension["max_score"])
            value = float(dimension["score"])
            if maximum <= 0 or not 0 <= value <= maximum:
                continue
            dimension_scores[str(dimension["dimension"])].append(value / maximum * 100)
    active_stages = [item for item in stages if item["job_id"] in job_ids and item["candidate_id"] in candidate_ids]
    screened = {item["candidate_id"] for item in valid_reports}
    funnel = [len(candidates), len(screened)]
    for minimum in (2, 3, 4):
        funnel.append(len({item["candidate_id"] for item in active_stages if STAGE_RANK.get(item["stage"], 0) >= minimum}))
    return {
        "candidate_count": len(candidates), "job_count": len(jobs),
        "average_score": round(sum(item["total_score"] for item in valid_reports) / len(valid_reports), 2) if valid_reports else None,
        "high_match_count": sum(score >= HIGH_MATCH_THRESHOLD for score in candidate_best.values()),
        "scores": [item["total_score"] for item in valid_reports],
        "job_averages": {job_id: round(sum(values) / len(values), 2) for job_id, values in job_scores.items()},
        "dimension_averages": {name: round(sum(values) / len(values), 2) for name, values in dimension_scores.items()},
        "funnel": dict(zip(FUNNEL_STAGES, funnel)), "report_count": len(valid_reports),
        "orphan_report_count": len(reports) - len(valid_reports),
    }
