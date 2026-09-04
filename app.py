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
    st.markdown("从岗位与简历出发，完成证据匹配、面试准备与招聘跟进。")
    st.caption("AI 辅助分析 · HR 确认与决策")
    try:
        metrics = dashboard_metrics(list_jobs(), list_candidates(), read_analytics())
    except (sqlite3.Error, OSError, ValueError):
        metrics = None
        st.warning("招聘数据暂时无法读取，请检查数据库配置与访问权限。已有记录不会因此被清空。")
    st.subheader("核心指标")
    metric_columns = st.columns(4)
    metric_columns[0].metric("候选人数", metrics["candidate_count"] if metrics else "—")
    metric_columns[1].metric("岗位数量", metrics["job_count"] if metrics else "—")
    metric_columns[2].metric("平均匹配分", "—" if not metrics or metrics["average_score"] is None else f"{metrics['average_score']:.2f}")
    metric_columns[3].metric("高匹配候选人", metrics["high_match_count"] if metrics else "—")
    st.caption(f"高匹配：候选人最高最新匹配分 ≥ {HIGH_MATCH_THRESHOLD:g}；仅供进一步评估，不代表录用结论。")
    st.subheader("开始工作")
    if metrics and not metrics["job_count"]:
        st.info("还没有岗位。先粘贴一份 JD，解析并保存岗位要求，再添加候选人。")
    elif metrics and not metrics["candidate_count"]:
        st.info("岗位已准备好。上传 PDF 或 DOCX 简历，检查解析结果并确认保存，即可开始匹配。")
    for column, title, description, page, label in zip(
        st.columns(3),
        ("01 · 明确岗位", "02 · 添加候选人", "03 · 评估匹配"),
        ("粘贴 JD，整理岗位要求与能力权重。", "上传 PDF / DOCX，人工复核后保存。", "选择岗位与候选人，查看得分和简历依据。"),
        ("pages/01_岗位管理.py", "pages/02_候选人.py", "pages/03_智能匹配.py"),
        ("岗位管理 →", "候选人 →", "智能匹配 →"),
    ):
        with column:
            with st.container(border=True):
                st.markdown(f"### {title}")
                st.write(description)
                st.page_link(page, label=label)
    st.page_link("pages/04_面试助手.py", label="面试助手 · 围绕具体经历准备问题 →")
    st.page_link("pages/05_招聘分析.py", label="招聘分析 · 查看匹配分布与招聘进展 →")
    st.divider()
    with st.expander("使用与数据说明"):
        st.write("未配置 API 时，可使用 JD Mock 示例和简历本地解析；Mock 岗位不代表实际 JD 的分析结果。")
        st.write("匹配依据岗位能力模型和简历证据，不自动淘汰候选人。简历经 HR 确认后才保存。")
        st.caption("当前没有登录与用户隔离。公开演示请仅使用虚构数据；SQLite 在云端不保证持久保存。不要将密钥或真实候选人记录上传 GitHub。")


if __name__ == "__main__":
    main()
