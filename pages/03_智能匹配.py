"""人工辅助人岗匹配，只读岗位和候选人，不自动淘汰。"""

import json
import sqlite3

import streamlit as st

from database.matching_records import list_candidates, list_jobs
from database.dashboard import save_match_report
from services.matching import MatchingError, build_rubric, calculate_match
from services.ui import apply_saas_theme

st.set_page_config(page_title="人岗匹配", page_icon="🔎", layout="wide")
apply_saas_theme("智能匹配")
st.title("人岗匹配")
st.info("仅辅助人工评估，不自动淘汰候选人。总分由岗位能力模型各维度得分相加，不调用大模型评分。")
try:
    jobs, candidates = list_jobs(), list_candidates()
except (sqlite3.Error, OSError, ValueError):
    st.error("无法读取岗位或候选人数据，请检查数据库及已保存记录。")
    st.stop()
if not jobs or not candidates:
    st.warning("请先在 JD 解析模块保存一个岗位，并在简历解析模块确认保存一个候选人。")
    st.stop()
job_id = st.selectbox("选择岗位", [item["id"] for item in jobs], format_func=lambda identifier: next(f"#{item['id']} · {item['label']} · {item['mode']}" for item in jobs if item["id"] == identifier))
candidate_id = st.selectbox("选择候选人", [item["id"] for item in candidates], format_func=lambda identifier: next(f"#{item['id']} · {item['label']} · {item['mode']}" for item in candidates if item["id"] == identifier))
job = next(item for item in jobs if item["id"] == job_id)
candidate = next(item for item in candidates if item["id"] == candidate_id)
selection = json.dumps([job, candidate], sort_keys=True, ensure_ascii=False)
if st.session_state.get("match_selection") != selection:
    for key in list(st.session_state):
        if key.startswith("match_criteria_") or key == "match_result":
            del st.session_state[key]
    st.session_state["match_selection"] = selection
if job["mode"] == "mock":
    st.warning("此岗位来自固定 Mock 示例，本次结果仅用于测试，不能作为真实岗位结论。")
try:
    defaults = build_rubric(job["data"])
except MatchingError as exc:
    st.error(str(exc))
    st.stop()
st.subheader("核对本次评分口径")
st.caption("权重来自已保存岗位，不可在此修改。默认指标为规则建议，请按岗位真实要求核对。未知指标留空将提示信息不足。")
with st.expander("评分规则与限制", expanded=False):
    st.write("同一维度的指标等分权重；明确实践描述或学历达标=1，技能栏自述=0.5，无明确证据=0。重复描述不加分；只看职位名称不加分。")
    st.write("confidence 是规则证据可信度（0～1），不是候选人能力概率。关键词、否定及职位识别是保守规则，可能漏识别，需要人工核对。")
    st.write("有证据的指标按权重计算覆盖率；覆盖不足 60% 优先输出信息不足，其余总分不足 60 输出匹配度较低，否则建议进一步评估。阈值是本地规则，不是经过验证的招聘标准。")
with st.form("match_form"):
    rubric = {}
    for index, dimension in enumerate(job["data"]["competency_model"]):
        name = dimension["dimension"]
        st.text(f"{name} · 满分 {dimension['weight']} · {dimension['description']}")
        value = st.text_area(f"{name}评分指标（每行一项）", value="\n".join(defaults[name]), key=f"match_criteria_{index}", height=90)
        rubric[name] = [line.strip() for line in value.splitlines() if line.strip()]
    submitted = st.form_submit_button("计算匹配结果", type="primary")
if submitted:
    st.session_state.pop("match_result", None)
    try:
        result = calculate_match(job["data"], candidate["data"], rubric)
        save_match_report(job_id, candidate_id, job["data"], candidate["data"], result)
        st.session_state["match_result"] = result
    except (MatchingError, ValueError) as exc:
        st.error(str(exc))
    except (sqlite3.Error, OSError):
        st.error("匹配结果已计算但统计快照保存失败，请检查数据库后重试。")
if "match_result" in st.session_state:
    result = st.session_state["match_result"]
    st.subheader("匹配结果")
    st.caption("以下为上次点击计算时的快照；修改评分指标后请重新计算。")
    st.metric("总分 / 100", result["total_score"])
    st.write("评估建议：", result["recommendation"])
    st.write("加权证据覆盖率：", f"{result['evidence_coverage']}%")
    st.warning(result["notice"])
    for dimension in result["dimensions"]:
        with st.expander(f"{dimension['dimension']} · {dimension['score']} / {dimension['max_score']}", expanded=True):
            st.text(dimension["reason"])
            st.write("confidence：", dimension["confidence"])
            for evidence in dimension["evidence_sources"]:
                st.caption("简历来源：" + evidence["source"])
                st.text(evidence["quote"])
            if not dimension["evidence_sources"]:
                st.text("暂无明确证据")
    for key, label in (("strengths", "优势"), ("risks", "风险与信息缺口"), ("questions_to_verify", "待核实问题")):
        st.subheader(label)
        if not result[key]:
            st.caption("暂无明确结论")
        for text in result[key]:
            st.text("• " + text)
    with st.expander("完整结果 JSON"):
        st.json(result)
