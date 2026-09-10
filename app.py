"""FF 人力工作台首页：AI 招聘工作驾驶舱。"""

import sqlite3
import streamlit as st

from database.activity import list_ai_usage
from database.dashboard import read_analytics
from database.matching_records import list_candidates, list_jobs
from services.ui import apply_saas_theme
from services.workspace_dashboard import calculate_workspace_dashboard
from services.workspace_ui import (
    render_ai_recruiting_summary,
    render_global_search,
    render_recruitment_alerts,
    render_recruitment_board,
    render_recruitment_metrics,
    render_today_schedule,
)


def main() -> None:
    st.set_page_config(page_title="FF 人力工作台", page_icon="💼", layout="wide")
    apply_saas_theme("首页")
    title, search = st.columns([2, 3], vertical_alignment="center")
    title.title("招聘工作台")
    title.caption("查看今天的任务、进展与招聘风险")
    with search:
        query = render_global_search()
    try:
        dashboard = calculate_workspace_dashboard(list_jobs(), list_candidates(), read_analytics(), list_ai_usage())
    except (sqlite3.Error, OSError, ValueError):
        st.error("招聘数据暂时无法读取，请稍后重新尝试。")
        st.stop()
    render_recruitment_metrics(dashboard["metrics"])
    render_ai_recruiting_summary(dashboard["ai_usage"])
    if dashboard["active_jobs"] == 0:
        st.info("还没有招聘中的岗位。")
        st.page_link("pages/01_岗位管理.py", label="创建第一个岗位 →")
    render_recruitment_board(dashboard["tasks"], query.strip())
    bottom = st.columns([3, 2])
    with bottom[0]:
        render_today_schedule(dashboard["schedule"])
    with bottom[1]:
        render_recruitment_alerts(dashboard["alerts"])

if __name__ == "__main__":
    main()
