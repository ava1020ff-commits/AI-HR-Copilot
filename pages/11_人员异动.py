"""人员异动分析页面。"""

import streamlit as st

from services.ui import apply_saas_theme, render_page_header, render_section_title

st.set_page_config(page_title="人员异动", page_icon="↔", layout="wide")
apply_saas_theme("人员异动")
render_page_header("人员异动", "跟进人员变化，关注新人留存并沉淀离职改善行动")

st.info("当前尚未接入员工异动和离职访谈数据。以下内容用于明确跟进流程，不代表已经发生人员异动。")

render_section_title("异动概览", "接入数据后按统一周期自动更新")
metrics = st.columns(4)
metrics[0].metric("本期入职", "—")
metrics[1].metric("本期离职", "—")
metrics[2].metric("新人留存率", "—")
metrics[3].metric("主动离职率", "—")

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
st.caption("暂无待跟进事项。接入人员异动数据后，这里将显示负责人、当前进度和下一步行动。")
st.caption("离职原因和访谈记录属于敏感人事信息，应配置访问权限并由 HR 人工确认；系统不自动判断个人去留。")
