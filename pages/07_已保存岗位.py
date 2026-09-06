"""岗位管理：结构化查看已保存岗位，并按需展开编辑。"""

import sqlite3

import streamlit as st

from database.jobs import list_saved_jobs, update_job
from services.jd_parser import JDParseError, LLMConfig, MAX_JD_LENGTH, parse_jd, parse_jd_local
from services.ui import apply_saas_theme, mode_label, render_empty_state, render_page_header, render_section_title, render_tags

st.set_page_config(page_title="岗位管理", page_icon="🗂️", layout="wide")
apply_saas_theme("已保存岗位")
render_page_header("岗位管理", "管理岗位信息、JD 与招聘进度", action_path="pages/01_岗位管理.py", action_label="＋ 创建岗位")

try:
    jobs = list_saved_jobs()
except (sqlite3.Error, OSError, ValueError):
    jobs = []
    st.error("暂时无法读取已保存岗位。")

if not jobs:
    render_empty_state("▣", "暂无已保存岗位", "创建并保存岗位后，可在这里查看和维护岗位信息。", action_path="pages/01_岗位管理.py", action_label="＋ 创建岗位")
    st.stop()

render_section_title("岗位列表", f"共 {len(jobs)} 个岗位")
selected_id = st.selectbox("选择岗位", [item["id"] for item in jobs], format_func=lambda value: next(item["job_title"] for item in jobs if item["id"] == value))
selected = next(item for item in jobs if item["id"] == selected_id)
result = selected["result"]

with st.container(border=True, key=f"job_detail_{selected_id}"):
    title_columns = st.columns([4, 1])
    title_columns[0].markdown(f"## {selected['job_title']}")
    title_columns[1].caption("招聘中")
    metadata = " · ".join(item for item in (selected["work_location"], selected["salary_range"], result.get("education"), result.get("experience")) if item)
    st.caption(metadata or "岗位信息待补充")
    summary = st.columns(3)
    summary[0].metric("能力维度", len(result.get("competency_model", [])))
    summary[1].metric("硬技能", len(result.get("hard_skills", [])))
    summary[2].metric("加分技能", len(result.get("bonus_skills", [])))
    st.markdown("### 核心能力")
    render_tags(result.get("hard_skills", []) + result.get("soft_skills", []))
    with st.expander("查看岗位职责与完整 JD"):
        st.text(selected["source_jd"])

with st.expander("编辑岗位", expanded=False):
    st.caption(f"当前保存方式：{mode_label(selected['mode'])}。更新后保留原岗位 ID。")
    mode_names = ("本地解析", "示例模式", "智能解析")
    current_mode = {"local": "本地解析", "mock": "示例模式", "llm": "智能解析"}.get(selected["mode"], "本地解析")
    edit_mode = st.radio("更新方式", mode_names, index=mode_names.index(current_mode), horizontal=True)
    use_local = edit_mode == "本地解析"
    use_mock = edit_mode == "示例模式"
    if use_mock:
        st.warning("示例模式会使用固定演示数据，请勿用于正式岗位。")
    elif use_local:
        st.caption("本地解析不发送数据到外部服务，结果需要人工复核。")
    else:
        st.caption("智能解析会将 JD 发送到已配置的 LLM 服务，请先移除敏感内容。")

    with st.form(f"edit_job_{selected_id}"):
        jd = st.text_area("岗位 JD", value=selected["source_jd"], height=320, max_chars=MAX_JD_LENGTH, key=f"edit_jd_{selected_id}")
        title = st.text_input("岗位名称", value=selected["job_title"], key=f"edit_title_{selected_id}")
        details = st.columns(2)
        work_location = details[0].text_input("工作地点", value=selected["work_location"], key=f"edit_location_{selected_id}")
        salary_range = details[1].text_input("薪资范围", value=selected["salary_range"], key=f"edit_salary_{selected_id}")
        consent = True if (use_local or use_mock) else st.checkbox("我确认允许将此 JD 发送到配置的 LLM 服务")
        submitted = st.form_submit_button("重新解析并更新", type="primary")

    if submitted:
        if not consent:
            st.error("请先确认发送 JD 的授权。")
        else:
            try:
                with st.spinner("正在更新岗位……"):
                    config = LLMConfig.from_env()
                    parsed = parse_jd_local(jd, title) if use_local else parse_jd(jd, config=config, use_mock=use_mock)
                    mode = "local" if use_local else "mock" if use_mock else "llm"
                    update_job(selected_id, jd, parsed, mode, work_location=work_location, salary_range=salary_range)
                st.success(f"岗位已更新 · ID {selected_id}")
                st.caption("岗位 ID 保持不变，已有匹配和面试记录仍与该岗位关联。")
            except JDParseError as exc:
                st.error(str(exc))
            except sqlite3.IntegrityError:
                st.error("更新后的内容与另一个已保存岗位重复，请检查后再试。")
            except (sqlite3.Error, OSError, ValueError):
                st.error("岗位更新失败，请检查数据库状态后重试。")
