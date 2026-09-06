"""Recruitment Dashboard：Plotly 图表与人工阶段记录。"""

import sqlite3

import plotly.graph_objects as go
import streamlit as st

from database.dashboard import STAGES, read_analytics, set_stage
from database.matching_records import list_candidates, list_jobs
from services.dashboard import HIGH_MATCH_THRESHOLD, dashboard_metrics, scoring_scope
from services.ui import apply_saas_theme, render_empty_state, render_page_header, render_section_title

st.set_page_config(page_title="招聘分析", page_icon="📊", layout="wide")
apply_saas_theme("招聘分析")
render_page_header("招聘分析", "通过招聘数据观察人才质量与招聘进度")
try:
    jobs, candidates, analytics = list_jobs(), list_candidates(), read_analytics()
    if jobs:
        selected_job = st.selectbox("统计岗位", [j["id"] for j in jobs], format_func=lambda value: next(j["label"] for j in jobs if j["id"] == value))
        scoped_reports = [r for r in analytics["reports"] if r["job_id"] == selected_job and r["candidate_id"] in {c["id"] for c in candidates}]
        scopes = list(dict.fromkeys(scoring_scope(r["report"]) for r in scoped_reports))
        if scopes:
            selected_scope = st.selectbox("评分规则版本", scopes, format_func=lambda value: f"版本 {scopes.index(value) + 1} · {sum(scoring_scope(r['report']) == value for r in scoped_reports)} 份报告")
            scoped_reports = [r for r in scoped_reports if scoring_scope(r["report"]) == selected_scope]
        scoped_ids = {r["candidate_id"] for r in scoped_reports}
        metrics = dashboard_metrics([j for j in jobs if j["id"] == selected_job], candidates, {
            "reports": scoped_reports,
            "stages": [s for s in analytics["stages"] if s["job_id"] == selected_job and s["candidate_id"] in scoped_ids],
        })
    else:
        metrics = dashboard_metrics(jobs, candidates, analytics)
except (sqlite3.Error, OSError, ValueError):
    st.error("Dashboard 数据读取或校验失败，请检查数据库记录。")
    st.stop()

columns = st.columns(4)
columns[0].metric("已确认保存候选人（全库）", metrics["candidate_count"])
columns[1].metric("匹配报告数", metrics["report_count"])
columns[2].metric("平均匹配分", "暂无数据" if metrics["average_score"] is None else f"{metrics['average_score']:.2f}")
columns[3].metric(f"高匹配报告数（≥{HIGH_MATCH_THRESHOLD:g} 分）", metrics["high_match_count"])
st.caption(f"以上数据来自所选岗位、使用同一评分规则生成的 {metrics['report_count']} 份最新匹配报告。没有生成报告的候选人不计入平均分；{HIGH_MATCH_THRESHOLD:g} 分是系统筛选参考值，不代表最终录用标准。不同岗位的平均分不建议直接比较。")
if metrics["orphan_report_count"]:
    st.warning(f"有 {metrics['orphan_report_count']} 条报告找不到当前岗位或候选人，已从统计中排除。")

if not metrics["report_count"]:
    render_empty_state("▥", "暂无招聘分析数据", "完成至少一份候选人匹配报告后，即可查看招聘漏斗与人才质量洞察。", action_path="pages/03_智能匹配.py", action_label="开始 AI 匹配")
    st.stop()

def no_data_figure(title: str, x_title: str = "") -> go.Figure:
    figure = go.Figure()
    figure.add_annotation(text="暂无可统计数据", x=0.5, y=0.5, xref="paper", yref="paper", showarrow=False)
    figure.update_layout(title=title, xaxis_title=x_title, template="plotly_white", height=380)
    return figure

render_section_title("人才质量洞察")
left, right = st.columns(2)
with left:
    if metrics["scores"]:
        distribution = go.Figure(go.Histogram(x=metrics["scores"], xbins={"start": 0, "end": 100, "size": 10}, marker_color="#0066CC"))
        distribution.update_layout(title="候选人匹配分分布", xaxis_title="匹配分", yaxis_title="人岗组合数", bargap=0.08, template="plotly_white", height=380)
    else:
        distribution = no_data_figure("候选人匹配分分布", "匹配分")
    st.plotly_chart(distribution, use_container_width=True, key="score_distribution")
with right:
    labels = {item["id"]: item["label"] for item in jobs}
    rows = [(labels.get(key, str(key)), metrics["report_count"]) for key in metrics["job_averages"]]
    if rows:
        job_chart = go.Figure(go.Bar(x=[row[1] for row in rows], y=[row[0] for row in rows], orientation="h", marker_color="#0066CC", text=[row[1] for row in rows], textposition="auto"))
        job_chart.update_layout(title="岗位匹配报告数量", xaxis_title="报告数量", yaxis_title="岗位", template="plotly_white", height=380)
    else:
        job_chart = no_data_figure("岗位匹配报告数量", "报告数量")
    st.plotly_chart(job_chart, use_container_width=True, key="job_average")

left, right = st.columns(2)
with left:
    dimensions = sorted(metrics["dimension_averages"].items(), key=lambda row: row[1])
    if dimensions:
        dimension_chart = go.Figure(go.Bar(x=[row[1] for row in dimensions], y=[row[0] for row in dimensions], orientation="h", marker_color="#0066CC", text=[row[1] for row in dimensions], textposition="auto"))
        dimension_chart.update_layout(title="能力维度平均得分率", xaxis_title="平均得分率（%）", yaxis_title="能力维度", xaxis_range=[0, 100], template="plotly_white", height=380)
    else:
        dimension_chart = no_data_figure("能力维度平均得分率", "平均得分率（%）")
    st.plotly_chart(dimension_chart, use_container_width=True, key="dimension_average")
with right:
    funnel = go.Figure(go.Bar(y=list(metrics["funnel"]), x=list(metrics["funnel"].values()), orientation="h", marker_color="#0066CC"))
    funnel.update_layout(title="记录数量（非转化漏斗）", template="plotly_white", height=380)
    st.plotly_chart(funnel, use_container_width=True, key="recruitment_funnel")

st.subheader("人工记录招聘阶段")
st.caption("首项是全库已确认保存的候选人，不是岗位投递人数；其余统计限定当前岗位和评分口径。后三阶段按人工记录阶段累计计数，不代表逐步转化率。记录 Offer 不会创建或发送 Offer。下方登记表可管理所有岗位组合。")
reports = analytics["reports"]
if not reports:
    st.info("暂无匹配报告。请先在人岗匹配页面计算一个人岗组合。")
else:
    job_names = {item["id"]: item["label"] for item in jobs}
    candidate_names = {item["id"]: item["label"] for item in candidates}
    valid = [item for item in reports if item["job_id"] in job_names and item["candidate_id"] in candidate_names]
    if valid:
        with st.form("stage_form"):
            pair = st.selectbox("选择人岗组合", [(item["job_id"], item["candidate_id"]) for item in valid], format_func=lambda value: f"{job_names[value[0]]} × {candidate_names[value[1]]}")
            stage = st.selectbox("实际招聘阶段", STAGES)
            confirmed = st.checkbox("我确认这是 HR 人工记录的实际阶段，不是系统自动决策")
            save = st.form_submit_button("保存阶段")
        if save:
            if not confirmed:
                st.error("请先确认阶段由 HR 人工判断。")
            else:
                try:
                    set_stage(pair[0], pair[1], stage)
                    st.success("阶段已记录。刷新页面可查看更新后的漏斗。")
                except (sqlite3.Error, OSError, ValueError) as exc:
                    st.error(str(exc))
