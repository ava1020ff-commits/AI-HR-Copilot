"""基于人工授权操作的候选人寻访入口，不自动抓取或联系。"""

import sqlite3

import streamlit as st

from database.candidates import save_candidate
from database.matching_records import list_jobs
from services.sourcing import PLATFORMS, boolean_search, csv_template, parse_import, search_terms
from services.ui import apply_saas_theme, render_ai_intro, render_empty_state, render_page_header, render_section_title

st.set_page_config(page_title="AI 候选人寻访", page_icon="🧭", layout="wide")
apply_saas_theme("候选人寻访")
render_page_header("AI 候选人寻访", "根据岗位要求生成候选人搜索策略与 Boolean Search")

try:
    jobs = list_jobs()
except (sqlite3.Error, OSError, ValueError):
    st.error("暂时无法读取岗位，请稍后重试。")
    st.stop()
if not jobs:
    render_empty_state("⌕", "暂无可寻访岗位", "请先创建并保存岗位，再生成搜索策略。", action_path="pages/01_岗位管理.py", action_label="＋ 创建岗位")
    st.stop()

job_id = st.selectbox("选择岗位", [item["id"] for item in jobs], format_func=lambda value: next(item["label"] for item in jobs if item["id"] == value))
job = next(item for item in jobs if item["id"] == job_id)
terms = search_terms(job["data"])
render_ai_intro("AI Sourcing", "从当前岗位名称和职业技能生成可复制的搜索条件。")
render_section_title("Boolean Search", "复制搜索式并在招聘平台内使用")
st.code(boolean_search(terms), language=None)
st.caption("仅包含岗位名称和职业技能。请在平台内复核地点、经验等条件；不要使用性别、年龄、婚育等敏感条件。")
for column, (platform, url) in zip(st.columns(2), PLATFORMS.items()):
    with column:
        st.link_button(f"前往 {platform}", url, use_container_width=True)
st.caption("平台跳转不会携带候选人数据，也不会自动执行搜索；请复制上方条件并在你的企业账号内操作。")

render_section_title("合规导入候选人", "上传经授权导出的 CSV，并在保存前人工确认")
st.download_button("下载 CSV 模板", csv_template(), "candidate-import-template.csv", "text/csv")
uploaded = st.file_uploader("上传已获授权的候选人 CSV", type=["csv"])
if uploaded:
    try:
        draft, source = parse_import(uploaded.getvalue())
        st.session_state["sourcing_draft"] = (draft, source)
    except ValueError as exc:
        st.error(str(exc))
if "sourcing_draft" in st.session_state:
    draft, source = st.session_state["sourcing_draft"]
    st.write("候选人：", draft["candidate_name"])
    st.write("来源编号/链接：", source)
    st.json(draft, expanded=False)
    confirm_rights = st.checkbox("我确认有权使用该资料，已遵守来源平台规则并取得必要授权")
    confirm_review = st.checkbox("我已人工复核职业字段，并确认不含联系方式及敏感筛选信息")
    if st.button("确认保存候选人", type="primary"):
        if not (confirm_rights and confirm_review):
            st.error("请完成两项人工确认后再保存。")
        else:
            try:
                candidate_id = save_candidate(draft, "local", confirmed=True)
                st.success(f"候选人已确认保存 · ID {candidate_id}。来源仅在当前导入页面显示，未写入匹配字段。")
            except (sqlite3.Error, OSError, ValueError) as exc:
                st.error(str(exc))

st.caption("合规说明：系统不会登录、抓取、绕过验证码或自动联系候选人；请遵守来源平台规则。")
