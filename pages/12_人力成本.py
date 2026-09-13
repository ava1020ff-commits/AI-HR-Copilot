"""人力成本分析页面。"""

import sqlite3
import streamlit as st

from services.ui import render_data_table

from database.hr_base_data import load_base_data
from services.human_cost import (
    calculate_dashboard,
    dashboard_csv,
)
from services.ui import apply_saas_theme, render_page_header, render_section_title

st.set_page_config(page_title="人力成本", page_icon="▤", layout="wide")
apply_saas_theme("人力成本")
render_page_header("人力成本", "基于基础数据自动核算人力分布、离职、绩效与续签指标")

try:
    base_data = load_base_data()
except (sqlite3.Error, OSError, ValueError):
    st.error("基础数据暂时无法读取，请到基础数据页面重新上传。")
    st.stop()

with st.expander("核算设置", expanded=False):
    settings = st.columns(3)
    with settings[0]:
        as_of = st.date_input("统计日期")
    with settings[1]:
        reminder_days = st.number_input("提醒窗口（天）", min_value=1, max_value=180, value=60)
    with settings[2]:
        pip_threshold = st.number_input("低绩效阈值", min_value=0.0, max_value=5.0, value=2.0, step=0.1)

dashboard = []
if base_data["updated_at"]:
    try:
        dashboard = calculate_dashboard(base_data["active"], base_data["departed"], base_data["hc"], as_of=as_of, reminder_days=int(reminder_days), pip_threshold=float(pip_threshold))
    except ValueError as exc:
        st.error(f"数据无法核算：{exc}")
else:
    st.info("尚未上传基础数据。")
    st.page_link("pages/10_基础数据.py", label="前往基础数据 →")

render_section_title("核算结果")
metrics = st.columns(4)
metrics[0].metric("实际在职人数", sum(int(row["实际在职"]) for row in dashboard) if dashboard else "—")
metrics[1].metric("本月离职人数", sum(int(row["离职人数"]) for row in dashboard) if dashboard else "—")
metrics[2].metric("PIP 预警人数", sum(int(row["PIP预警"]) for row in dashboard) if dashboard else "—")
metrics[3].metric("二次续签人数", sum(int(row["60天内二次续签"]) for row in dashboard) if dashboard else "—")

if dashboard:
    render_section_title("人力分布看板", "按二级部门和属地汇总")
    render_data_table(row_height=44, data=dashboard, hide_index=True, width="stretch")
    st.download_button("导出人力分布看板", dashboard_csv(dashboard), "human-cost-dashboard.csv", "text/csv", type="primary")
else:
    st.caption("基础数据准备完成后，这里将自动显示人力分布看板。")

workflow = (
    ("1", "更新员工花名册", "导入最新人员信息，确认部门、岗位、在职与离职状态。"),
    ("2", "匹配绩效数据", "按员工和月份匹配绩效，单独列出缺失或重复记录。"),
    ("3", "核算离职率", "按确认的人员范围和统计周期核算离职率。"),
    ("4", "识别 PIP 预警", "依据已确认的连续低绩效规则生成待 HR 复核名单。"),
    ("5", "核算二次续签", "结合合同到期日与续签状态识别本期二次续签人员。"),
    ("6", "复核并输出周报", "解释异常变化，完成 HR 确认后输出人力成本数据报表。"),
)
with st.expander("查看计算流程与规则", expanded=False):
    st.caption("更新基础数据 → 核算指标 → 复核异常 → 输出周报")
    for number, title, description in workflow:
        st.markdown(f"**{number}. {title}**　{description}")

with st.expander("查看指标说明", expanded=False):
    st.caption("每项指标都要明确统计周期、人员范围和计算规则")
    render_data_table(row_height=44, data=
        [
            {"指标": "主动离职率", "普通解释": "统计期内主动离职人数占平均在职人数的比例", "当前状态": "待接入"},
            {"指标": "PIP 绩效预警", "普通解释": "满足已确认绩效规则、需要 HR 复核的人数", "当前状态": "待接入"},
            {"指标": "二次续签", "普通解释": "合同进入第二次续签节点且需要跟进的人数", "当前状态": "待接入"},
            {"指标": "人力成本", "普通解释": "统计期内经确认纳入的薪酬及相关用工成本", "当前状态": "待接入"},
        ],
        hide_index=True,
        width="stretch",
        column_config={"指标": st.column_config.TextColumn(width="medium"), "普通解释": st.column_config.TextColumn(width="large")},
    )
    st.caption("PIP、续签和离职指标只用于工作提醒与数据分析；人员决定必须由授权 HR 根据公司制度人工确认。")
