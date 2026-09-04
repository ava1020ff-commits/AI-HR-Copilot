"""AI Recruitment Copilot 企业工作台首页。"""

import sqlite3
import streamlit as st

from database.dashboard import read_analytics
from database.matching_records import list_candidates, list_jobs
from services.dashboard import HIGH_MATCH_THRESHOLD, dashboard_metrics
from services.ui import apply_saas_theme


def main() -> None:
    st.set_page_config(page_title="AI Recruitment Copilot", page_icon="💼", layout="wide")
    apply_saas_theme("首页")
    st.title("AI Recruitment Copilot")
    st.markdown("面向现代招聘团队的一体化智能工作台。将岗位解析、候选人管理、证据化匹配、面试准备与招聘分析集中在清晰、可审计的流程中。")
    st.caption("AI 提供辅助，关键招聘判断始终由 HR 完成。")
    try:
        metrics = dashboard_metrics(list_jobs(), list_candidates(), read_analytics())
    except (sqlite3.Error, OSError, ValueError):
        metrics = {"candidate_count": 0, "job_count": 0, "average_score": None, "high_match_count": 0}
    st.subheader("核心指标")
    metric_columns = st.columns(4)
    metric_columns[0].metric("候选人数", metrics["candidate_count"])
    metric_columns[1].metric("岗位数量", metrics["job_count"])
    metric_columns[2].metric("平均匹配分", "—" if metrics["average_score"] is None else f"{metrics['average_score']:.2f}")
    metric_columns[3].metric("高匹配候选人", metrics["high_match_count"])
    st.caption(f"高匹配口径：候选人最高最新匹配分 ≥ {HIGH_MATCH_THRESHOLD:g}。")
    st.subheader("招聘流程，一处协同")
    for column, title, description in zip(
        st.columns(3),
        ("结构化人才数据", "可解释智能决策", "专业面试与分析"),
        ("将岗位要求与候选人经历整理为标准化、可复核的数据。", "基于岗位能力模型和简历证据计算匹配结果，完整展示依据。", "围绕真实经历准备针对性问题，并用 Dashboard 观察招聘进展。"),
    ):
        with column:
            with st.container(border=True):
                st.markdown(f"### {title}")
                st.write(description)
    st.divider()
    st.caption("数据默认保存在本地 SQLite。请勿将密钥、真实简历或数据库文件提交到代码仓库。")


if __name__ == "__main__":
    main()
