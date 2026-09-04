"""面试提纲：引用 JD、能力模型、简历和已验证的匹配报告。"""

import json
import sqlite3

import streamlit as st

from database.interview_records import read_jd
from database.matching_records import list_candidates, list_jobs
from services.interview import CATEGORIES, InterviewError, generate_interview
from services.matching import MatchingError, calculate_match
from services.ui import apply_saas_theme

st.set_page_config(page_title="面试助手", page_icon="🎙️", layout="wide")
apply_saas_theme("面试助手")
st.title("面试助手")
st.caption("JD + 能力模型 + 简历 + 匹配报告 → 可追溯的针对性问题")
st.info("本地生成，无需 API。不生成录用结论，不要求提供前雇主机密或个人敏感信息。")
try:
    jobs, candidates = list_jobs(), list_candidates()
except (sqlite3.Error, OSError, ValueError):
    st.error("无法读取岗位或候选人，请检查数据库及已保存记录。")
    st.stop()
if not jobs or not candidates:
    st.warning("请先保存岗位 JD，并确认保存候选人简历。")
    st.stop()
job_id = st.selectbox("选择岗位", [item["id"] for item in jobs], format_func=lambda value: next(f"#{item['id']} · {item['label']} · {item['mode']}" for item in jobs if item["id"] == value))
candidate_id = st.selectbox("选择候选人", [item["id"] for item in candidates], format_func=lambda value: next(f"#{item['id']} · {item['label']}" for item in candidates if item["id"] == value))
job = next(item for item in jobs if item["id"] == job_id)
candidate = next(item for item in candidates if item["id"] == candidate_id)
try:
    jd = read_jd(job_id)
except (sqlite3.Error, OSError, ValueError):
    st.error("无法读取岗位 JD 原文，请重新选择或保存岗位。")
    st.stop()
selection = json.dumps([job, candidate], sort_keys=True, ensure_ascii=False)
use_current = st.session_state.get("match_selection") == selection and "match_result" in st.session_state
current_report = st.session_state["match_result"] if use_current else None
signature = json.dumps([selection, jd, current_report], sort_keys=True, ensure_ascii=False)
if st.session_state.get("interview_signature") != signature:
    st.session_state.pop("interview_result", None)
    st.session_state["interview_signature"] = signature
if job["mode"] == "mock":
    st.warning("此岗位来自固定 Mock 示例，生成的面试提纲仅用于演示。")
if use_current:
    st.caption("将使用匹配页面当前报告，保留 HR 调整过的评分指标，并核验报告与当前数据一致。")
else:
    st.warning("没有这组人岗的当前匹配报告：点击生成时将按默认评分口径计算报告。若需自定义指标，请先在人岗匹配页面计算。")
if st.button("生成面试问题", type="primary"):
    st.session_state.pop("interview_result", None)
    try:
        report = current_report if use_current else calculate_match(job["data"], candidate["data"])
        guide = generate_interview(job["data"], jd, candidate["data"], report)
        st.session_state["interview_result"] = {"guide": guide, "report": report}
    except (MatchingError, InterviewError) as exc:
        st.error(str(exc))
if "interview_result" in st.session_state:
    saved = st.session_state["interview_result"]
    guide = saved["guide"]
    st.success("面试提纲已生成，请 HR 根据面试时长选用并核对引用。")
    for omission in guide["omissions"]:
        st.warning(omission)
    for category in CATEGORIES:
        st.subheader(category)
        if not guide["categories"][category]:
            st.caption("当前简历缺少可用经历，不生成泛泛问题，请先补充材料。")
        for index, item in enumerate(guide["categories"][category], 1):
            with st.expander(f"{index}. {item['evaluation_dimension']}", expanded=True):
                st.text(item["question"])
                st.write("考察目的：", item["purpose"])
                for key, label in (("follow_up", "追问"), ("good_signals", "积极信号"), ("risk_signals", "待核实信号")):
                    st.markdown(f"**{label}**")
                    for text in item[key]:
                        st.text("• " + text)
                st.caption("简历引用位置：" + item["sources"]["resume"]["source"])
                st.caption(f"匹配报告：{item['matching_context']['score']}/{item['matching_context']['max_score']}；confidence={item['matching_context']['confidence']}")
    st.info(guide["notice"])
    with st.expander("本次使用的匹配报告"):
        st.json(saved["report"])
    with st.expander("完整面试提纲 JSON（含引用依据）"):
        st.json(guide)
