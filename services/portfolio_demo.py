"""Read-only synthetic portfolio example; no database writes or API calls."""

from services.matching import calculate_match


def build_demo() -> tuple[dict, dict, dict]:
    """Return fresh fictional records and a report computed by the real rules."""
    job = {
        "job_title": "AI 产品实习生 · 虚构示例", "education": "未提及",
        "experience": "未提及", "hard_skills": ["需求分析", "RAG", "SQL"],
        "soft_skills": [], "bonus_skills": [],
        "competency_model": [
            {"dimension": "产品能力", "weight": 40, "description": "需求分析"},
            {"dimension": "AI应用", "weight": 35, "description": "RAG"},
            {"dimension": "数据能力", "weight": 25, "description": "SQL"},
        ],
    }
    candidate = {
        "candidate_name": "示例候选人 A（虚构）", "education": [],
        "work_experience": [], "internships": [], "certificates": [],
        "projects": ["负责需求分析并完成校园问答产品的需求文档"],
        "skills": ["RAG"],
    }
    return job, candidate, calculate_match(job, candidate)
