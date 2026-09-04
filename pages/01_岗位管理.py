"""JD 解析页面：输入、解析、保存和结构化展示。"""

import sqlite3

import streamlit as st

from database.jobs import save_job
from services.jd_parser import JDParseError, LLMConfig, MAX_JD_LENGTH, parse_jd
from services.ui import apply_saas_theme

st.set_page_config(page_title="JD 解析", page_icon="📋", layout="wide")
apply_saas_theme("岗位管理")
st.title("JD 解析")
st.caption("粘贴岗位描述，解析要求并保存岗位。")
config = LLMConfig.from_env()
use_mock = st.checkbox("使用示例模式", value=not bool(config.api_key))
if use_mock:
    st.warning("示例模式：展示固定的 Python 工程师岗位，与输入内容无关，仅供体验。")
else:
    st.info("真实模式：点击解析会将 JD 发送到配置的 LLM 服务。请先移除个人信息及敏感内容。")
with st.expander("设置与技术说明"):
    st.write("通过环境变量或 Streamlit Secrets 配置 LLM_API_KEY、LLM_MODEL、LLM_BASE_URL（默认 https://api.openai.com/v1）。环境变量优先，修改后重启服务。")
    st.caption("接口需支持 Chat Completions 的 JSON 模式。未配置时使用示例模式（内部标记 mock）。岗位保存于 SQLite。")

with st.form("jd_form"):
    jd = st.text_area("粘贴岗位 JD", height=320, max_chars=MAX_JD_LENGTH, placeholder="请输入岗位名称、职责、任职要求及加分项……")
    consent = True if use_mock else st.checkbox("我确认允许将此 JD 发送到配置的 LLM 服务")
    submitted = st.form_submit_button("解析岗位", type="primary")

if submitted:
    st.session_state.pop("jd_result", None)
    if not consent:
        st.error("请先确认发送 JD 的授权。")
    else:
        try:
            with st.spinner("正在解析并保存岗位……"):
                result = parse_jd(jd, config=config, use_mock=use_mock)
                mode = "mock" if use_mock else "llm"
                job_id = save_job(jd, result, mode)
                st.session_state["jd_result"] = {"result": result, "mode": mode, "id": job_id}
        except JDParseError as exc:
            st.error(str(exc))
        except (sqlite3.Error, OSError):
            st.error("岗位保存失败，请检查数据库目录权限或锁定状态后重试；本次未确认保存成功。")

if "jd_result" in st.session_state:
    saved = st.session_state["jd_result"]
    result = saved["result"]
    st.success(f"岗位已保存 · ID {saved['id']} · {'示例模式' if saved['mode'] == 'mock' else '智能解析'}")
    st.caption("以下是上次成功提交的结果；修改输入后请重新解析。胜任力模型为建议，需 HR 复核。")
    if saved["mode"] == "mock":
        st.warning("以下为固定岗位示例，不代表对输入内容的真实分析。")
    st.subheader(result["job_title"])
    st.write("学历要求：", result["education"])
    st.write("经验要求：", result["experience"])
    for column, label, key in zip(st.columns(3), ("硬技能", "软技能", "加分技能"), ("hard_skills", "soft_skills", "bonus_skills")):
        with column:
            st.markdown(f"### {label}")
            for skill in result[key]:
                st.text(f"• {skill}")
            if not result[key]:
                st.caption("未提及")
    st.subheader("胜任力模型")
    if result["competency_model"]:
        st.table([{"维度": item["dimension"], "权重 (%)": item["weight"], "说明": item["description"]} for item in result["competency_model"]])
    else:
        st.info("JD 信息不足，暂无胜任力建议。")
    with st.expander("查看完整 JSON", expanded=True):
        st.json(result)
