"""人力成本分析页面。"""

import streamlit as st

from services.human_cost import (
    ACTIVE_COLUMNS,
    DEPARTED_COLUMNS,
    HC_COLUMNS,
    calculate_dashboard,
    csv_template,
    dashboard_csv,
    read_csv,
)
from services.ui import apply_saas_theme, render_page_header, render_section_title

st.set_page_config(page_title="人力成本", page_icon="▤", layout="wide")
apply_saas_theme("人力成本")
render_page_header("人力成本", "")

st.info("上传数据只在当前会话中处理，不写入招聘数据库。在职名单需包含 M/P/S/O 序列，HC 表需填写总 HC 和各序列 HC。请使用脱敏数据，并在发布报表前由 HR 复核。")
render_section_title("准备数据")
data_columns = st.columns(3)
data_sources = (
    ("在职人员", "人员、序列、合同与近期绩效", ACTIVE_COLUMNS, "active-employees.csv", "active_people"),
    ("离职人员", "本期离职人员及离职类型", DEPARTED_COLUMNS, "departed-employees.csv", "departed_people"),
    ("HC", "部门、属地及 M/P/S/O 计划人数", HC_COLUMNS, "headcount.csv", "hc_data"),
)
uploaded_files = []
for column, (title, description, fields, filename, key) in zip(data_columns, data_sources):
    with column:
        with st.container(border=True, key=f"data_card_{key}"):
            st.markdown(f"### {title}")
            st.caption(description)
            st.download_button("下载模板", csv_template(fields), filename, "text/csv", use_container_width=True, key=f"template_{key}")
            uploaded_files.append(st.file_uploader(f"上传{title}", type=["csv"], key=key, label_visibility="collapsed"))
active_file, departed_file, hc_file = uploaded_files

with st.expander("核算设置", expanded=False):
    settings = st.columns(3)
    with settings[0]:
        as_of = st.date_input("统计日期")
    with settings[1]:
        reminder_days = st.number_input("提醒窗口（天）", min_value=1, max_value=180, value=60)
    with settings[2]:
        pip_threshold = st.number_input("低绩效阈值", min_value=0.0, max_value=5.0, value=2.0, step=0.1)

dashboard = []
if active_file and departed_file and hc_file:
    try:
        active_rows = read_csv(active_file.getvalue(), ACTIVE_COLUMNS)
        departed_rows = read_csv(departed_file.getvalue(), DEPARTED_COLUMNS)
        hc_rows = read_csv(hc_file.getvalue(), HC_COLUMNS)
        dashboard = calculate_dashboard(active_rows, departed_rows, hc_rows, as_of=as_of, reminder_days=int(reminder_days), pip_threshold=float(pip_threshold))
    except (UnicodeDecodeError, ValueError) as exc:
        st.error(f"数据无法核算：{exc}")

render_section_title("核算结果")
metrics = st.columns(4)
metrics[0].metric("实际在职人数", sum(int(row["实际在职"]) for row in dashboard) if dashboard else "—")
metrics[1].metric("本月离职人数", sum(int(row["离职人数"]) for row in dashboard) if dashboard else "—")
metrics[2].metric("PIP 预警人数", sum(int(row["PIP预警"]) for row in dashboard) if dashboard else "—")
metrics[3].metric("二次续签人数", sum(int(row["60天内二次续签"]) for row in dashboard) if dashboard else "—")

if dashboard:
    render_section_title("人力分布看板", "按二级部门和属地汇总")
    st.dataframe(dashboard, hide_index=True, width="stretch")
    st.download_button("导出人力分布看板", dashboard_csv(dashboard), "human-cost-dashboard.csv", "text/csv", type="primary")
else:
    st.caption("上传三份数据后，这里将显示人力分布看板。")

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
    st.dataframe(
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
