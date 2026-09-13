"""招聘工作台：指标、待办、岗位进展、AI 工具。"""

from datetime import datetime
import sqlite3

import streamlit as st

from database.dashboard import read_analytics
from database.matching_records import list_candidates, list_jobs
from services.ui import apply_saas_theme
from services.workspace_dashboard import WORKSPACE_TIMEZONE, calculate_recruitment_overview
from services.workspace_ui import (
    apply_workspace_layout,
    render_recruitment_metrics,
    render_action_queue,
    render_job_progress,
    render_ai_tools,
)


def main() -> None:
    st.set_page_config(page_title="FF 人力工作台", page_icon="💼", layout="wide")
    apply_saas_theme("首页")
    apply_workspace_layout()
    with st.container(key="recruitment_home"):
        now = datetime.now(WORKSPACE_TIMEZONE)
        with st.container(key="workspace_header"):
            title, filters = st.columns([3, 2], vertical_alignment="bottom")
            title.title("招聘工作台")
            title.caption(f"{now:%Y年%m月%d日} · 北京时间 · 当前招聘概况")
        try:
            with st.spinner("正在读取招聘数据……", show_time=True):
                jobs, candidates, analytics = list_jobs(), list_candidates(), read_analytics()
            job_names = {item["id"]: item["label"] for item in jobs}
            if st.session_state.get("workspace_job", "all") not in ["all", *job_names]:
                st.session_state["workspace_job"] = "all"
            with filters:
                selected_value = st.selectbox(
                    "岗位筛选", ["all", *job_names],
                    format_func=lambda value: "全部岗位" if value == "all" else job_names[value],
                    key="workspace_job", disabled=not jobs,
                    help="暂无岗位可筛选" if not jobs else "同步筛选指标、待办和岗位进展",
                    on_change=lambda: st.toast("岗位筛选已更新", icon=":material/check_circle:"),
                )
            selected_job = None if selected_value == "all" else selected_value
            dashboard = calculate_recruitment_overview(jobs, candidates, analytics, selected_job=selected_job, now=now)
        except (sqlite3.Error, OSError, ValueError):
            st.error("招聘数据暂时无法读取，请稍后重新尝试。")
            if st.button("重新加载", key="workspace_retry", type="primary"):
                st.rerun()
            st.stop()
        render_recruitment_metrics(dashboard["metrics"])
        if selected_job is not None:
            st.caption("岗位筛选同时作用于指标、待办与岗位进展；仅统计已有匹配或阶段记录的关联候选人，未关联简历不归入该岗位。")
        render_action_queue(dashboard["actions"])
        render_job_progress(dashboard["job_progress"])
        render_ai_tools()


if __name__ == "__main__":
    main()
