"""AI Recruitment Copilot 企业工作台首页。"""

import sqlite3
import streamlit as st

from database.dashboard import read_analytics
from database.matching_records import list_candidates, list_jobs
from services.dashboard import HIGH_MATCH_THRESHOLD, dashboard_metrics
from services.ui import apply_saas_theme
from services.portfolio_demo import build_demo
from services.match_explanation import render_dimension


def main() -> None:
    st.set_page_config(page_title="AI Recruitment Copilot", page_icon="💼", layout="wide")
    apply_saas_theme("首页")
    st.title("AI Recruitment Copilot")
    with st.container(key="home_primary_action"):
        st.page_link("pages/01_岗位管理.py", label="开始工作 · 岗位管理 →")
    with st.expander("首次访问？查看虚构案例", expanded=False):
        st.caption("无需密钥或上传文件；只读演示，不写入招聘数据。")
        if st.button("查看示例匹配", key="portfolio_demo"):
            demo_job, demo_candidate, report = build_demo()
            st.write(demo_job["job_title"] + " × " + demo_candidate["candidate_name"])
            st.write(f"证据覆盖分：{report['total_score']} / 100 · {report['recommendation']}")
            for dimension in report["dimensions"]:
                st.text(f"{dimension['dimension']}：{dimension['score']} / {dimension['max_score']}")
                render_dimension(dimension)
            st.write("待核实项")
            for risk in report["risks"]:
                st.text(risk)
            st.write("推荐面试问题")
            for question in report["questions_to_verify"]:
                st.text(question)
            st.caption(report["notice"])
    try:
        metrics = dashboard_metrics(list_jobs(), list_candidates(), read_analytics())
    except (sqlite3.Error, OSError, ValueError):
        metrics = None
        st.warning("招聘数据暂时无法读取，请检查数据库配置与访问权限。已有记录不会因此被清空。")
    st.subheader("核心指标")
    metric_columns = st.columns(4)
    metric_columns[0].metric("候选人数", metrics["candidate_count"] if metrics else "—")
    metric_columns[1].metric("岗位数量", metrics["job_count"] if metrics else "—")
    metric_columns[2].metric("已生成报告（人岗组合）", metrics["report_count"] if metrics else "—")
    metric_columns[3].metric("已有报告候选人", metrics["funnel"]["已生成匹配报告"] if metrics else "—")
    st.caption("候选人数来自已确认保存的记录；每个人岗组合仅保留最新报告。分数请在招聘分析中按岗位与评分口径查看，不跨模型排名。")
    st.subheader("开始工作")
    if metrics and not metrics["job_count"]:
        st.caption("暂无岗位，先添加一份岗位描述即可开始。")
    elif metrics and not metrics["candidate_count"]:
        st.caption("岗位已准备好，添加候选人并确认保存后即可匹配。")
    for column, title, description, page, label in zip(
        st.columns(3),
        ("01 · 明确岗位", "02 · 添加候选人", "03 · 评估匹配"),
        ("粘贴 JD，整理岗位要求与能力权重。", "上传 PDF / DOCX，人工复核后保存。", "选择岗位与候选人，查看得分和简历依据。"),
        ("pages/01_岗位管理.py", "pages/02_候选人.py", "pages/03_智能匹配.py"),
        ("岗位管理 →", "候选人 →", "智能匹配 →"),
    ):
        with column:
            with st.container(border=True, key=f"workflow_{title[:2]}"):
                st.markdown(f"### {title}")
                st.write(description)
                st.page_link(page, label=label)
    st.page_link("pages/04_面试助手.py", label="面试助手 · 围绕具体经历准备问题 →")
    st.page_link("pages/05_招聘分析.py", label="招聘分析 · 查看匹配分布与招聘进展 →")
    st.divider()
    with st.expander("关于项目与源码"):
        st.write("面向招聘资料整理与人工评估的 AI 辅助原型，覆盖岗位解析、候选人管理、证据匹配、面试准备和招聘分析。")
        st.write("Python · Streamlit · SQLite · Plotly。匹配分由可复现规则计算；未配置 API 时不使用大模型解析 JD。")
        st.markdown("[查看源码与项目说明](https://github.com/ava1020ff-commits/AI-HR-Copilot)")
        st.caption("演示原型，不是已投入企业生产的招聘系统；不自动决定候选人去留。")
    with st.expander("使用与数据说明"):
        st.write("未配置 API 时，可使用 JD Mock 示例和简历本地解析；Mock 岗位不代表实际 JD 的分析结果。")
        st.write("匹配依据岗位能力模型和简历证据，不自动淘汰候选人。简历经 HR 确认后才保存。")
        st.caption("当前没有登录与用户隔离。公开演示请仅使用虚构数据；SQLite 在云端不保证持久保存。不要将密钥或真实候选人记录上传 GitHub。")


if __name__ == "__main__":
    main()
