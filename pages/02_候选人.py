"""上传、解析、人工修订、确认保存的简历工作流。"""

import hashlib
import sqlite3

import streamlit as st

from database.candidates import save_candidate
from services.jd_parser import LLMConfig
from services.resume_parser import FIELDS, ResumeError, extract_resume, parse_resume, sanitize_text, validate_resume
from services.ui import apply_saas_theme

st.set_page_config(page_title="简历解析", page_icon="📄", layout="wide")
apply_saas_theme("候选人")
st.title("简历解析")
st.caption("上传简历 → 解析 → 展示及人工修改 → 确认保存")
st.info("仅保留职业相关字段。性别、年龄、照片、婚姻状况不作为匹配字段。原文件不落盘；保存前请人工复核并移除遗漏的敏感信息。")
config = LLMConfig.from_env()
use_local = st.checkbox("使用本地规则解析（无需 API）", value=not bool(config.api_key), key="resume_local")
if use_local:
    st.warning("本地模式按教育、工作、实习、项目等章节标题提取，复杂排版可能漏项；请补全后保存。不是固定 Mock 数据。")
else:
    st.caption("使用 LLM_API_KEY、LLM_MODEL、LLM_BASE_URL 配置；失败不会自动切换到本地模式。")
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
                st.error("保存失败，请检查 SQLite 目录权限或数据库锁定状态。修改内容仍保留，可重试。")
    if "resume_saved" in st.session_state:
        saved = st.session_state["resume_saved"]
        st.success(f"上次确认的简历已保存 · 候选人 ID {saved['id']}")
        st.caption("下方是已保存快照；继续修改表单后需要再次确认保存。")
        st.json(saved["result"])
    else:
        with st.expander("查看初始解析 JSON"):
            st.json(draft["result"])
