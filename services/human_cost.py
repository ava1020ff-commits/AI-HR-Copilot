"""人力成本 CSV 校验与确定性指标核算。"""

from __future__ import annotations

import csv
from datetime import date, datetime, timedelta
from io import StringIO

ACTIVE_COLUMNS = (
    "员工编号", "姓名", "二级部门", "属地", "序列", "入职日期", "合同到期日", "续签次数",
    "绩效1", "绩效2", "绩效3",
)
DEPARTED_COLUMNS = ("员工编号", "姓名", "二级部门", "属地", "入职日期", "离职日期", "离职类型")
HC_COLUMNS = ("二级部门", "属地", "月初HC", "M月初HC", "P月初HC", "S月初HC", "O月初HC")


def csv_template(columns: tuple[str, ...]) -> bytes:
    buffer = StringIO()
    csv.writer(buffer).writerow(columns)
    return buffer.getvalue().encode("utf-8-sig")


def read_csv(content: bytes, required: tuple[str, ...]) -> list[dict[str, str]]:
    text = content.decode("utf-8-sig")
    reader = csv.DictReader(StringIO(text))
    missing = [column for column in required if column not in (reader.fieldnames or [])]
    if missing:
        raise ValueError("缺少字段：" + "、".join(missing))
    rows = [{key: (value or "").strip() for key, value in row.items()} for row in reader]
    return [row for row in rows if any(row.values())]


def _date(value: str, field: str) -> date:
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValueError(f"{field} 必须使用 YYYY-MM-DD 格式：{value}") from exc


def _number(value: str, field: str) -> float:
    try:
        return float(value)
    except ValueError as exc:
        raise ValueError(f"{field} 必须是数字：{value}") from exc


def calculate_dashboard(
    active: list[dict[str, str]],
    departed: list[dict[str, str]],
    hc_rows: list[dict[str, str]],
    *,
    as_of: date,
    reminder_days: int = 60,
    pip_threshold: float = 2.0,
) -> list[dict[str, object]]:
    """按二级部门和属地核算人力分布；仅生成提醒，不作人事决定。"""
    keys = {(row["二级部门"], row["属地"]) for row in active + departed + hc_rows}
    result = []
    deadline = as_of + timedelta(days=reminder_days)
    for department, location in sorted(keys):
        current = [row for row in active if (row["二级部门"], row["属地"]) == (department, location)]
        leavers = [row for row in departed if (row["二级部门"], row["属地"]) == (department, location) and _date(row["离职日期"], "离职日期").year == as_of.year and _date(row["离职日期"], "离职日期").month == as_of.month]
        hc_matches = [row for row in hc_rows if (row["二级部门"], row["属地"]) == (department, location)]
        opening_hc = sum(int(_number(row["月初HC"], "月初HC")) for row in hc_matches)
        probation = sum(as_of <= _date(row["入职日期"], "入职日期") + timedelta(days=180) <= deadline for row in current)
        renewal = sum(as_of <= _date(row["合同到期日"], "合同到期日") <= deadline for row in current)
        second_renewal = sum(as_of <= _date(row["合同到期日"], "合同到期日") <= deadline and int(_number(row["续签次数"], "续签次数")) == 1 for row in current)
        pip_counts = [sum(_number(row[field], field) <= pip_threshold for field in ("绩效1", "绩效2", "绩效3") if row[field]) for row in current]
        pip_hit = sum(count >= 2 for count in pip_counts)
        pip_warning = sum(count == 1 for count in pip_counts)
        average_hc = (opening_hc + len(current)) / 2
        voluntary = sum(row["离职类型"] == "主动离职" for row in leavers)
        planned_by_level = {level: sum(int(_number(row[f"{level}月初HC"], f"{level}月初HC")) for row in hc_matches) for level in "MPSO"}
        actual_by_level = {level: sum(row["序列"].upper() == level for row in current) for level in "MPSO"}
        result.append({
            "二级部门": department,
            "属地": location,
            "月初HC": opening_hc,
            "实际在职": len(current),
            "HC差额": opening_hc - len(current),
            **{f"{level}月初HC": planned_by_level[level] for level in "MPSO"},
            **{f"{level}实际在职": actual_by_level[level] for level in "MPSO"},
            "60天内试用期到期": probation,
            "60天内合同续签": renewal,
            "60天内二次续签": second_renewal,
            "PIP命中": pip_hit,
            "PIP预警": pip_warning,
            "离职人数": len(leavers),
            "主动离职率": round(voluntary / average_hc * 100, 2) if average_hc else 0.0,
        })
    return result


def dashboard_csv(rows: list[dict[str, object]]) -> bytes:
    if not rows:
        return b""
    buffer = StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8-sig")
