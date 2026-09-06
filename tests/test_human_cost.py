from datetime import date

import pytest

from services.human_cost import ACTIVE_COLUMNS, calculate_dashboard, csv_template, read_csv


def test_template_round_trip() -> None:
    assert read_csv(csv_template(ACTIVE_COLUMNS), ACTIVE_COLUMNS) == []


def test_missing_columns_are_rejected() -> None:
    with pytest.raises(ValueError, match="缺少字段"):
        read_csv("姓名\n测试\n".encode("utf-8"), ACTIVE_COLUMNS)


def test_dashboard_calculates_group_metrics() -> None:
    active = [{"员工编号": "1", "姓名": "甲", "二级部门": "安全部", "属地": "上海", "序列": "M", "入职日期": "2026-04-01", "合同到期日": "2026-10-01", "续签次数": "1", "绩效1": "2", "绩效2": "2", "绩效3": "3"}]
    departed = [{"员工编号": "2", "姓名": "乙", "二级部门": "安全部", "属地": "上海", "入职日期": "2025-01-01", "离职日期": "2026-09-05", "离职类型": "主动离职"}]
    hc = [{"二级部门": "安全部", "属地": "上海", "月初HC": "2", "M月初HC": "1", "P月初HC": "1", "S月初HC": "0", "O月初HC": "0"}]

    row = calculate_dashboard(active, departed, hc, as_of=date(2026, 9, 1))[0]

    assert row["实际在职"] == 1
    assert row["HC差额"] == 1
    assert row["M月初HC"] == 1
    assert row["M实际在职"] == 1
    assert row["60天内二次续签"] == 1
    assert row["PIP命中"] == 1
    assert row["离职人数"] == 1
    assert row["主动离职率"] == 66.67
