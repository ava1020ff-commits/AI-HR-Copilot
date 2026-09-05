"""JD 解析页面：输入、解析、保存和结构化展示。"""

import sqlite3

import streamlit as st

from database.jobs import save_job
from services.jd_parser import JDParseError, LLMConfig, MAX_JD_LENGTH, parse_jd, parse_jd_local
from services.ui import apply_saas_theme, render_page_header, render_section_title, render_tags

st.set_page_config(page_title="创建岗位", page_icon="📋", layout="wide")
apply_saas_theme("JD 解析")
render_page_header("创建岗位", "粘贴岗位 JD，通过 AI 或本地规则整理岗位要求", action_path="pages/07_已保存岗位.py", action_label="查看岗位列表")
render_section_title("创建招聘岗位", "选择解析方式并填写岗位信息")
config = LLMConfig.from_env()

mode_label = st.radio("解析方式", ("本地解析", "示例模式", "智能解析"), horizontal=True)
use_mock = mode_label == "示例模式"
use_local = mode_label == "本地解析"
if use_mock:
    st.warning("示例模式：展示固定的 Python 工程师岗位，与输入内容无关，仅供体验。")
elif not use_local:
    st.info("真实模式：点击解析会将 JD 发送到配置的 LLM 服务。请先移除个人信息及敏感内容。")
else:
    st.info("本地解析会读取你粘贴的 JD，不发送到外部服务。规则识别能力有限，结果必须人工复核。")

with st.form("jd_form"):
    jd = st.text_area("粘贴岗位 JD", height=320, max_chars=MAX_JD_LENGTH, placeholder="请输入岗位名称、职责、任职要求及加分项……", key="jd_input")
    local_title = st.text_input("岗位名称（本地解析建议填写）", key="local_job_title") if use_local else ""
    details = st.columns(2)
    work_location = details[0].text_input("工作地点", placeholder="例如：上海 / 远程", key="job_location")
    salary_range = details[1].text_input("薪资范围", placeholder="例如：15K–25K · 14薪", key="job_salary_range")
    consent = True if (use_mock or use_local) else st.checkbox("我确认允许将此 JD 发送到配置的 LLM 服务")
    submitted = st.form_submit_button("✦ AI 解析并保存岗位", type="primary")

if submitted:
    st.session_state.pop("jd_result", None)
    if not consent:
        st.error("请先确认发送 JD 的授权。")
    else:
        try:
            with st.spinner("正在解析并保存岗位……"):
                result = parse_jd_local(jd, local_title) if use_local else parse_jd(jd, config=config, use_mock=use_mock)
                mode = "local" if use_local else "mock" if use_mock else "llm"
                job_id = save_job(jd, result, mode, work_location=work_location, salary_range=salary_range)
                st.session_state["jd_result"] = {
                    "result": result, "mode": mode, "id": job_id,
                    "work_location": work_location, "salary_range": salary_range,
                }
        except JDParseError as exc:
            st.error(str(exc))
        except sqlite3.IntegrityError:
            st.error("更新后的内容与另一个已保存岗位重复，请检查后再试。")
        except (sqlite3.Error, OSError, ValueError):
            st.error("岗位保存失败，请检查数据库目录权限或锁定状态后重试；本次未确认保存成功。")

if "jd_result" in st.session_state:
    saved = st.session_state["jd_result"]
    result = saved["result"]
    mode_name = {"mock": "示例模式", "local": "本地解析", "llm": "智能解析"}.get(saved["mode"], saved["mode"])
    st.success(f"岗位已保存 · ID {saved['id']} · {mode_name}")
    st.caption("以下是上次成功提交的结果；修改输入后请重新解析。胜任力模型为建议，需 HR 复核。")
    if saved["mode"] == "mock":
        st.warning("以下为固定岗位示例，不代表对输入内容的真实分析。")
    render_section_title("AI JD Analysis", "解析结果已保存，请复核关键信息", ai=True)
    st.markdown(f"### {result['job_title']}")
    metadata = st.columns(2)
    metadata[0].write(f"工作地点：{saved.get('work_location') or '未填写'}")
    metadata[1].write(f"薪资范围：{saved.get('salary_range') or '未填写'}")
    st.write("学历要求：", result["education"])
    st.write("经验要求：", result["experience"])
    for column, label, key in zip(st.columns(3), ("硬技能", "软技能", "加分技能"), ("hard_skills", "soft_skills", "bonus_skills")):
        with column:
            st.markdown(f"### {label}")
            render_tags(result[key])
    st.subheader("胜任力模型")
    if result["competency_model"]:
        st.dataframe(
            [{"维度": item["dimension"], "权重 (%)": item["weight"], "说明": item["description"]} for item in result["competency_model"]],
            hide_index=True,
            width="stretch",
            column_config={"权重 (%)": st.column_config.NumberColumn("权重 (%)", format="%d", width="small")},
        )
    else:
        st.info("JD 信息不足，暂无胜任力建议。")
    with st.expander("查看完整 JSON", expanded=True):
        st.json(result)
