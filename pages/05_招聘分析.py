"""Recruitment Dashboard：Plotly 图表与人工阶段记录。"""

import sqlite3

import plotly.graph_objects as go
import streamlit as st

from database.dashboard import STAGES, read_analytics, set_stage
from database.matching_records import list_candidates, list_jobs
from services.dashboard import HIGH_MATCH_THRESHOLD, dashboard_metrics
from services.ui import apply_saas_theme

st.set_page_config(page_title="Recruitment Dashboard", page_icon="📊", layout="wide")
apply_saas_theme("招聘分析")
st.title("Recruitment Dashboard")
st.caption("仅统计已保存的数据；不推测招聘阶段，不执行自动淘汰或录用。")
try:
    jobs, candidates, analytics = list_jobs(), list_candidates(), read_analytics()
    metrics = dashboard_metrics(jobs, candidates, analytics)
except (sqlite3.Error, OSError, ValueError):
    st.error("Dashboard 数据读取或校验失败，请检查数据库记录。")
    st.stop()

columns = st.columns(4)
columns[0].metric("候选人数", metrics["candidate_count"])
columns[1].metric("岗位数量", metrics["job_count"])
columns[2].metric("平均匹配分", "暂无数据" if metrics["average_score"] is None else f"{metrics['average_score']:.2f}")
columns[3].metric(f"高匹配候选人数（≥{HIGH_MATCH_THRESHOLD:g}）", metrics["high_match_count"])
st.caption(f"平均分基于 {metrics['report_count']} 个人岗组合的最新报告；高匹配人数按候选人的最高最新分去重统计。")
if metrics["orphan_report_count"]:
    st.warning(f"有 {metrics['orphan_report_count']} 条报告找不到当前岗位或候选人，已从统计中排除。")

def no_data_figure(title: str, x_title: str = "") -> go.Figure:
    figure = go.Figure()
    figure.add_annotation(text="暂无可统计数据", x=0.5, y=0.5, xref="paper", yref="paper", showarrow=False)
    figure.update_layout(title=title, xaxis_title=x_title, template="plotly_white", height=380)
    return figure

left, right = st.columns(2)
with left:
    if metrics["scores"]:
        distribution = go.Figure(go.Histogram(x=metrics["scores"], xbins={"start": 0, "end": 100, "size": 10}, marker_color="#2563EB"))
        distribution.update_layout(title="候选人匹配分分布", xaxis_title="匹配分", yaxis_title="人岗组合数", bargap=0.08, template="plotly_white", height=380)
    else:
        distribution = no_data_figure("候选人匹配分分布", "匹配分")
    st.plotly_chart(distribution, use_container_width=True, key="score_distribution")
with right:
    labels = {item["id"]: item["label"] for item in jobs}
    rows = sorted(((labels.get(key, f"已删除岗位 #{key}"), value) for key, value in metrics["job_averages"].items()), key=lambda row: row[1])
    if rows:
        job_chart = go.Figure(go.Bar(x=[row[1] for row in rows], y=[row[0] for row in rows], orientation="h", marker_color="#0F766E", text=[row[1] for row in rows], textposition="auto"))
        job_chart.update_layout(title="不同岗位平均匹配度", xaxis_title="平均匹配分", yaxis_title="岗位", xaxis_range=[0, 100], template="plotly_white", height=380)
    else:
        job_chart = no_data_figure("不同岗位平均匹配度", "平均匹配分")
    st.plotly_chart(job_chart, use_container_width=True, key="job_average")

left, right = st.columns(2)
with left:
    dimensions = sorted(metrics["dimension_averages"].items(), key=lambda row: row[1])
    if dimensions:
        dimension_chart = go.Figure(go.Bar(x=[row[1] for row in dimensions], y=[row[0] for row in dimensions], orientation="h", marker_color="#7C3AED", text=[row[1] for row in dimensions], textposition="auto"))
        dimension_chart.update_layout(title="能力维度平均得分率", xaxis_title="平均得分率（%）", yaxis_title="能力维度", xaxis_range=[0, 100], template="plotly_white", height=380)
    else:
        dimension_chart = no_data_figure("能力维度平均得分率", "平均得分率（%）")
    st.plotly_chart(dimension_chart, use_container_width=True, key="dimension_average")
with right:
    funnel = go.Figure(go.Funnel(y=list(metrics["funnel"]), x=list(metrics["funnel"].values()), textinfo="value+percent initial", marker={"color": ["#334155", "#2563EB", "#7C3AED", "#EA580C", "#16A34A"]}))
    funnel.update_layout(title="招聘漏斗", template="plotly_white", height=380)
    st.plotly_chart(funnel, use_container_width=True, key="recruitment_funnel")

st.subheader("人工记录招聘阶段")
st.caption("“收到简历”来自已确认保存的候选人；“AI辅助筛选”来自已保存匹配报告。后三阶段只来自此处 HR 人工记录。记录 Offer 仅表示已发生，不会创建或发送 Offer。")
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
