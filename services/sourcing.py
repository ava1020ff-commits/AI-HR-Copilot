"""合规寻访辅助：生成职业搜索词并校验人工录入，不访问招聘平台。"""

import csv
import io

from services.resume_parser import FIELDS, validate_resume

PLATFORMS = {"BOSS 直聘": "https://www.zhipin.com/", "猎聘": "https://www.liepin.com/"}


def search_terms(job: dict) -> list[str]:
    """从岗位职业字段生成可复制的去重关键词。"""
    terms = [job.get("job_title", ""), *job.get("hard_skills", []), *job.get("soft_skills", [])]
    return list(dict.fromkeys(str(term).strip() for term in terms if str(term).strip()))[:12]


def boolean_search(terms: list[str]) -> str:
    """Format search terms as a readable, platform-neutral Boolean query."""
    cleaned = [str(term).strip().replace('"', "") for term in terms if str(term).strip()]
    if not cleaned:
        return ""
    title, *skills = cleaned
    if not skills:
        return f'"{title}"'
    skill_group = "\n  OR ".join(f'"{skill}"' for skill in skills)
    return f'"{title}"\nAND (\n  {skill_group}\n)'


def csv_template() -> str:
    return "candidate_name,education,work_experience,internships,projects,skills,certificates,source_reference\n"


def parse_import(content: bytes) -> tuple[dict, str]:
    """Parse exactly one UTF-8 CSV row; pipe separates repeated values."""
    if not content or len(content) > 200_000:
        raise ValueError("请选择不超过 200 KB 的 CSV 文件。")
    try:
        rows = list(csv.DictReader(io.StringIO(content.decode("utf-8-sig"))))
    except (UnicodeDecodeError, csv.Error):
        raise ValueError("CSV 必须使用 UTF-8 编码。") from None
    expected = {"candidate_name", *FIELDS, "source_reference"}
    if len(rows) != 1 or set(rows[0]) != expected:
        raise ValueError("每次只导入一位候选人，且表头必须与模板完全一致。")
    row = rows[0]
    source = row.pop("source_reference", "").strip()
    if not source or len(source) > 300:
        raise ValueError("请填写不超过 300 字的来源编号或授权页面链接。")
    data = {key: [item.strip() for item in row[key].split("|") if item.strip()] for key in FIELDS}
    data["candidate_name"] = row["candidate_name"].strip()
    return validate_resume(data, require_name=True), source
