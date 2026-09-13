"""人员异动分析页面。"""

import sqlite3
from datetime import date, datetime
import streamlit as st

from database.hr_base_data import load_base_data
from services.ui import apply_saas_theme, render_page_header, render_section_title

st.set_page_config(page_title="人员异动", page_icon="↔", layout="wide")
apply_saas_theme("人员异动")
render_page_header("人员异动", "跟进人员变化，关注新人留存并沉淀离职改善行动")

try:
    base_data = load_base_data()
except (sqlite3.Error, OSError, ValueError):
    st.error("基础数据暂时无法读取，请到基础数据页面重新上传。")
    st.stop()

today = date.today()
active = base_data["active"]
departed = base_data["departed"]
def month_matches(value: str) -> bool:
    try:
        parsed = datetime.strptime(value, "%Y-%m-%d").date()
        return parsed.year == today.year and parsed.month == today.month
    except (TypeError, ValueError):
        return False

new_hires = sum(month_matches(row.get("入职日期", "")) for row in active)
leavers = sum(month_matches(row.get("离职日期", "")) for row in departed)
voluntary = sum(month_matches(row.get("离职日期", "")) and row.get("离职类型") == "主动离职" for row in departed)
opening = max(len(active) - new_hires + leavers, 0)
average = (opening + len(active)) / 2
retention_pool = [row for row in active + departed if month_matches(row.get("入职日期", ""))]
retained_ids = {row.get("员工编号") for row in active if month_matches(row.get("入职日期", ""))}
retention = len(retained_ids) / len(retention_pool) * 100 if retention_pool else None

if not base_data["updated_at"]:
    st.info("尚未上传基础数据。")
    st.page_link("pages/10_基础数据.py", label="前往基础数据 →")

render_section_title("异动概览", "接入数据后按统一周期自动更新")
metrics = st.columns(4)
metrics[0].metric("本月入职", new_hires if base_data["updated_at"] else "—")
metrics[1].metric("本月离职", leavers if base_data["updated_at"] else "—")
metrics[2].metric("本月新人留存率", f"{retention:.1f}%" if retention is not None else "暂无数据")
metrics[3].metric("本月主动离职率", f"{voluntary / average * 100:.1f}%" if average else "暂无数据")

steps = (
    ("1", "登记人员异动", "确认入职、转岗、晋升和离职记录及生效日期。"),
    ("2", "跟踪新人留存", "按入职批次观察关键周期留存，识别需要关注的团队。"),
    ("3", "安排离职访谈", "由 HR 与离职员工开展一对一访谈，记录事实与员工反馈。"),
    ("4", "归因流失痛点", "区分岗位、管理、发展、薪酬等因素，保留原始依据。"),
    ("5", "制定优化方案", "明确改善动作、负责人、完成时间和验证指标。"),
    ("6", "复盘改善效果", "按周期检查行动进展及新人留存、离职率的变化。"),
)
with st.expander("查看异动跟进流程", expanded=False):
    st.caption("记录异动 → 跟踪留存 → 离职访谈 → 流失归因 → 制定方案 → 效果复盘")
    for number, title, description in steps:
        st.markdown(f"**{number}. {title}**　{description}")

render_section_title("待跟进事项")
if leavers:
    st.write(f"本月有 {leavers} 条离职记录，其中主动离职 {voluntary} 条；请确认离职访谈和原因归档是否完成。")
else:
    st.caption("本月暂无离职记录。")
st.caption("离职原因和访谈记录属于敏感人事信息，应配置访问权限并由 HR 人工确认；系统不自动判断个人去留。")
