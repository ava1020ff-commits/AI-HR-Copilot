"""上传、解析、人工修订、确认保存的简历工作流。"""

import hashlib
import sqlite3

import streamlit as st

from database.candidates import save_candidate
from database.matching_records import list_candidates
from services.candidate_search import filter_candidates
from services.jd_parser import LLMConfig
from services.resume_parser import FIELDS, ResumeError, extract_resume, parse_resume, sanitize_text, validate_resume
from services.ui import apply_saas_theme

st.set_page_config(page_title="简历解析", page_icon="📄", layout="wide")
apply_saas_theme("候选人")
st.title("简历解析")
st.caption("上传简历 → 解析 → 展示及人工修改 → 确认保存")
st.info("仅保留职业相关字段。性别、年龄、照片、婚姻状况不作为匹配字段。原文件不落盘；保存前请人工复核并移除遗漏的敏感信息。")
config = LLMConfig.from_env()
use_local = st.checkbox("使用本地解析", value=not bool(config.api_key), key="resume_local")
if use_local:
    st.warning("本地解析按简历章节提取内容，复杂排版可能漏项；请复核补全后确认保存。")
else:
    st.caption("智能解析失败时不会自动切换到本地解析。")
with st.expander("设置与技术说明"):
    st.write("智能解析使用 LLM_API_KEY、LLM_MODEL、LLM_BASE_URL 配置；本地解析无需 API。确认保存的记录存入 SQLite。")
uploaded = st.file_uploader("上传简历（PDF / DOCX，最大 10 MB）", type=["pdf", "docx"], key="resume_upload")
content = uploaded.getvalue() if uploaded is not None else b""
source = hashlib.sha256(content).hexdigest() + (uploaded.name if uploaded is not None else "") + str(use_local)
if st.session_state.get("resume_source") != source:
    for key in list(st.session_state):
        if key.startswith("resume_edit_") or key in ("resume_draft", "resume_saved", "resume_reviewed", "resume_consent"):
            del st.session_state[key]
    st.session_state["resume_source"] = source

consent = True
if not use_local:
    st.warning("AI 模式会把提取的简历文本发送到配置的 LLM 服务。常见敏感片段会过滤，但不能保证完全脱敏。请仅上传已获授权的简历。")
    consent = st.checkbox("我已获得授权，允许将此简历文本发送给配置的 LLM 服务", key="resume_consent")
if st.button("解析简历", type="primary", disabled=uploaded is None):
    st.session_state.pop("resume_draft", None)
    st.session_state.pop("resume_saved", None)
    for key in list(st.session_state):
        if key.startswith("resume_edit_") or key == "resume_reviewed":
            del st.session_state[key]
    if not consent:
        st.error("请先确认简历发送授权。")
    else:
        try:
            with st.spinner("正在提取文字并解析……"):
                text = extract_resume(uploaded.name, content)
                result = parse_resume(text, use_local=use_local, config=config)
                st.session_state["resume_draft"] = {"result": result, "text": sanitize_text(text), "mode": "local" if use_local else "llm"}
        except ResumeError as exc:
            st.error(str(exc))

if "resume_draft" in st.session_state:
    draft = st.session_state["resume_draft"]
    st.subheader("解析结果 · 待 HR 确认")
    st.caption("当前尚未自动保存。每行一条记录；可增加、删除或改写内容。姓名只用于识别候选人，不用于匹配。")
    with st.expander("查看提取文本（已过滤常见敏感片段，可能有漏项）"):
        st.text(draft["text"])
    with st.form("resume_review"):
        edited = {"candidate_name": st.text_input("候选人姓名", value=draft["result"]["candidate_name"], key="resume_edit_name", max_chars=100)}
        for key, label in FIELDS.items():
            value = st.text_area(label + "（每行一条）", value="\n".join(draft["result"][key]), height=110, key="resume_edit_" + key)
            edited[key] = [line.strip() for line in value.splitlines() if line.strip()]
        reviewed = st.checkbox("我已核对所有字段，移除了敏感信息，并确认保存", key="resume_reviewed")
        save = st.form_submit_button("确认保存", type="primary")
    if save:
        st.session_state.pop("resume_saved", None)
        if not reviewed:
            st.error("请先勾选人工复核确认。")
        else:
            try:
                result = validate_resume(edited, require_name=True)
                candidate_id = save_candidate(result, draft["mode"], confirmed=True)
                st.session_state["resume_saved"] = {"id": candidate_id, "result": result}
            except ResumeError as exc:
                st.error(str(exc))
            except (sqlite3.Error, OSError):
                st.error("保存失败，修改内容仍保留，请稍后重试或联系维护者检查存储权限。")
    if "resume_saved" in st.session_state:
        saved = st.session_state["resume_saved"]
        st.success(f"上次确认的简历已保存 · 候选人 ID {saved['id']}")
        st.caption("下方是已保存快照；继续修改表单后需要再次确认保存。")
        st.json(saved["result"])
    else:
        with st.expander("查看初始解析 JSON"):
            st.json(draft["result"])

st.divider()
st.subheader("已保存候选人")
st.caption("仅展示经 HR 确认保存的记录。搜索和筛选不会改变匹配分数或招聘状态。")
try:
    records = list_candidates()
except (sqlite3.Error, OSError, ValueError):
    st.error("候选人列表读取失败，请检查数据库配置与权限。")
else:
    if not records:
        st.info("暂无已保存候选人，请先上传简历并确认保存。")
    else:
        query = st.text_input("搜索候选人", placeholder="姓名、ID、技能、项目或经历；多个词用空格分隔", key="candidate_query")
        education_options = sorted({item for record in records for item in record["data"].get("education", [])})
        skill_options = sorted({item for record in records for item in record["data"].get("skills", [])})
        columns = st.columns(2)
        education = columns[0].selectbox("教育记录", [""] + education_options, format_func=lambda value: value or "全部", key="candidate_education")
        skill = columns[1].selectbox("技能", [""] + skill_options, format_func=lambda value: value or "全部", key="candidate_skill")
        def clear_filters() -> None:
            for key in ("candidate_query", "candidate_education", "candidate_skill"):
                st.session_state[key] = ""
        st.button("清空筛选", on_click=clear_filters)
        filtered = filter_candidates(records, query, education, skill)
        st.caption(f"找到 {len(filtered)} / {len(records)} 位候选人 · 教育记录按简历原文筛选，不推断学历等级。")
        if not filtered:
            st.info("没有符合条件的候选人，请调整关键词或清空筛选。")
        else:
            st.dataframe([
                {"ID": record["id"], "姓名": record["data"].get("candidate_name", ""),
                 "教育记录": "；".join(record["data"].get("education", [])),
                 "技能": "、".join(record["data"].get("skills", []))}
                for record in filtered
            ], hide_index=True, use_container_width=True)
            chosen = st.selectbox("查看候选人详情", [record["id"] for record in filtered],
                format_func=lambda identifier: next(f"{r['label']} · ID {identifier}" for r in filtered if r["id"] == identifier))
            data = next(record["data"] for record in filtered if record["id"] == chosen)
            with st.expander("职业经历与技能详情"):
                for field, label in FIELDS.items():
                    st.markdown(f"**{label}**")
                    st.text("\n".join(data.get(field, [])) or "未提供")
