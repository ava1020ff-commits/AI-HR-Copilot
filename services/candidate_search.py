"""只搜索职业相关字段；不修改候选人或匹配结果。"""

from services.resume_parser import FIELDS


def filter_candidates(records: list[dict], query: str = "", education: str = "", skill: str = "") -> list[dict]:
    """关键词按空格拆分且全部匹配，学历和技能按原始条目精确筛选。"""
    terms = query.casefold().split()
    result = []
    for record in records:
        data = record["data"]
        parts = [str(record["id"]), data.get("candidate_name", "")]
        for field in FIELDS:
            parts.extend(data.get(field, []))
        text = " ".join(parts).casefold()
        if not all(term in text for term in terms):
            continue
        if education and education not in data.get("education", []):
            continue
        if skill and skill not in data.get("skills", []):
            continue
        result.append(record)
    return result
