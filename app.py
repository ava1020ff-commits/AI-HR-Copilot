"""HireMind AI 招聘工作台首页。"""

import sqlite3
import streamlit as st

from database.dashboard import read_analytics
from database.matching_records import list_candidates, list_jobs
from services.dashboard import dashboard_metrics
from services.ui import apply_saas_theme, render_ai_intro, render_empty_state, render_page_header, render_section_title
from services.portfolio_demo import build_demo
from services.match_explanation import render_dimension


def main() -> None:
    st.set_page_config(page_title="HireMind AI", page_icon="💼", layout="wide")
    apply_saas_theme("首页")
    render_page_header("招聘工作台", "集中查看岗位、候选人与 AI 招聘进展", action_path="pages/01_岗位管理.py", action_label="＋ 创建岗位")
    st.markdown("### 早上好 👋")
    st.caption("这是你当前的招聘进展")
    try:
        jobs = list_jobs()
        candidates = list_candidates()
        analytics = read_analytics()
        metrics = dashboard_metrics(jobs, candidates, analytics)
    except (sqlite3.Error, OSError, ValueError):
        jobs, candidates = [], []
        analytics = {"reports": [], "stages": []}
        metrics = None
        st.warning("招聘数据暂时无法读取，请检查数据库配置与访问权限。已有记录不会因此被清空。")
    render_section_title("工作概览")
    with st.container(key="home_metrics"):
        metric_columns = st.columns(4)
        metric_columns[0].metric("在招岗位", metrics["job_count"] if metrics else "—")
        metric_columns[1].metric("候选人才", metrics["candidate_count"] if metrics else "—")
        metric_columns[2].metric("AI 匹配报告", metrics["report_count"] if metrics else "—")
        metric_columns[3].metric("进入面试", metrics["funnel"]["进入面试"] if metrics else "—")

    render_section_title("招聘进展", "按岗位查看当前 AI 评估进度")
    focus_message = "已有匹配结果，建议按岗位查看待核实项和招聘进展。"
    focus_path, focus_label = "pages/05_招聘分析.py", "查看招聘分析 →"
    if metrics and not metrics["job_count"]:
        focus_message, focus_path, focus_label = "先创建岗位并确认岗位要求。", "pages/01_岗位管理.py", "＋ 创建岗位"
    elif metrics and not metrics["candidate_count"]:
        focus_message, focus_path, focus_label = "岗位已准备好，导入候选人后即可开始匹配。", "pages/02_候选人.py", "＋ 导入候选人"
    elif metrics and not metrics["report_count"]:
        focus_message, focus_path, focus_label = "岗位和候选人已准备好，可以生成第一份匹配报告。", "pages/03_智能匹配.py", "✦ 开始 AI 匹配"
    with st.container(border=True, key="recruitment_focus"):
        st.write(focus_message)
        st.page_link(focus_path, label=focus_label)
    if jobs:
        report_counts = {}
        for report in analytics["reports"]:
            report_counts[report["job_id"]] = report_counts.get(report["job_id"], 0) + 1
        job_columns = st.columns(2)
        for index, job in enumerate(jobs[:6]):
            with job_columns[index % 2]:
                with st.container(border=True, key=f"home_job_{job['id']}"):
                    st.markdown(f"### {job['label']}")
                    details = " · ".join(
                        item for item in (job.get("work_location"), job.get("salary_range")) if item
                    )
                    st.caption(details or "工作地点与薪资待补充")
                    report_count = report_counts.get(job["id"], 0)
                    st.progress(min(report_count / max(len(candidates), 1), 1.0))
                    st.caption(f"候选人才 {len(candidates)} · AI 匹配 {report_count}")
                    st.page_link("pages/07_已保存岗位.py", label="查看岗位 →")
        st.page_link("pages/07_已保存岗位.py", label="查看全部岗位 →")
    else:
        render_empty_state("▣", "暂无在招岗位", "创建岗位后，可在这里查看候选人与 AI 匹配进展。", action_path="pages/01_岗位管理.py", action_label="＋ 创建岗位")

    render_ai_intro("AI Recruiting Copilot", "让 AI 帮你完成招聘中的高频任务")
    render_section_title("快捷操作")
    quick_actions = st.columns(4)
    actions = (
        ("pages/01_岗位管理.py", "新增岗位"),
        ("pages/02_候选人.py", "导入候选人"),
        ("pages/03_智能匹配.py", "开始匹配"),
        ("pages/06_候选人寻访.py", "候选人寻访"),
    )
    for column, (path, label) in zip(quick_actions, actions):
        with column:
            st.page_link(path, label=f"{label} →")

    render_section_title("最近候选人", "最新确认加入人才库的候选人")
    if candidates:
        st.dataframe([
            {"姓名": item["label"], "核心技能": "、".join(item["data"].get("skills", [])[:3]) or "待补充", "操作": "可进行 AI 匹配"}
            for item in candidates[:5]
        ], hide_index=True, width="stretch")
        st.page_link("pages/02_候选人.py", label="查看全部候选人 →")
    else:
        render_empty_state("♙", "暂无候选人", "导入候选人后，可进行 AI 人岗匹配与面试评估。", action_path="pages/02_候选人.py", action_label="＋ 导入候选人")

    if metrics and not any((metrics["job_count"], metrics["candidate_count"], metrics["report_count"])):
        with st.expander("首次访问？查看虚构案例", expanded=False):
            st.caption("只读演示，不写入招聘数据。")
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


if __name__ == "__main__":
    main()
