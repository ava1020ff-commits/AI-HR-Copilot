"""根据岗位 JD 生成可直接使用的 BOSS 直聘沟通话术。"""

import json

import streamlit as st
import streamlit.components.v1 as components

from database.activity import try_record_ai_usage
from services.boss_messaging import BossMessageError, generate_boss_message
from services.jd_parser import LLMConfig, MAX_JD_LENGTH
from services.ui import apply_saas_theme, render_page_header, render_section_title


def render_copy_button(text: str, label: str, key: str) -> None:
    """提供浏览器剪贴板按钮，并兼容不支持 Clipboard API 的浏览器。"""
    payload = json.dumps(text, ensure_ascii=False).replace("</", "<\\/")
    components.html(
        f"""<button id="copy-{key}" type="button">{label}</button><span id="status-{key}" aria-live="polite"></span>
<style>
body {{ margin: 0; font-family: sans-serif; display: flex; justify-content: flex-end; align-items: center; gap: 8px; }}
button {{ min-height: 44px; padding: 8px 16px; border: 1px solid #dfe3ea; border-radius: 8px; background: #fff; color: #2563eb; cursor: pointer; font-size: 14px; }}
button:hover {{ background: #eff6ff; }} span {{ color: #667085; font-size: 12px; white-space: nowrap; }}
</style>
<script>
const value = {payload};
const button = document.getElementById('copy-{key}');
const status = document.getElementById('status-{key}');
button.addEventListener('click', async () => {{
  try {{ await navigator.clipboard.writeText(value); }}
  catch (_) {{
    const area = document.createElement('textarea'); area.value = value; document.body.appendChild(area);
    area.select(); document.execCommand('copy'); area.remove();
  }}
  status.textContent = '已复制'; setTimeout(() => status.textContent = '', 1600);
}});
</script>""",
        height=48,
    )


def render_result_card(icon: str, title: str, text: str, key: str, *, complete: bool = False) -> None:
    with st.container(border=True, key=f"boss_result_{key}"):
        heading, action = st.columns([4, 1], vertical_alignment="center")
        heading.markdown(f"### {icon} {title}")
        with action:
            render_copy_button(text, "一键复制完整话术" if complete else "复制", key)
        st.write(text)


st.set_page_config(page_title="BOSS沟通话术生成", page_icon="💬", layout="wide")
apply_saas_theme("BOSS沟通话术")
render_page_header("BOSS沟通话术生成", "粘贴岗位JD，AI自动生成更自然、更高效的候选人沟通话术")

with st.form("boss_message_form"):
    jd = st.text_area(
        "岗位 JD",
        height=320,
        max_chars=MAX_JD_LENGTH,
        placeholder="请粘贴岗位JD，包括岗位职责、任职要求、薪资福利等信息……",
        key="boss_jd_input",
    )
    submitted = st.form_submit_button("生成沟通话术", type="primary")

if submitted:
    st.session_state.pop("boss_message_result", None)
    if not jd.strip():
        st.warning("请先输入岗位JD")
    elif len(jd.strip()) < 20:
        st.warning("JD信息较少，建议补充岗位职责、任职要求或薪资信息后再生成。")
    else:
        try:
            with st.spinner("正在分析JD并生成招聘沟通话术……"):
                st.session_state["boss_message_result"] = generate_boss_message(jd, LLMConfig.from_env())
                try_record_ai_usage("boss_message")
        except (BossMessageError, ValueError):
            st.error("生成失败，请稍后重新尝试。")

if "boss_message_result" in st.session_state:
    result = st.session_state["boss_message_result"]
    render_section_title("生成结果", "发送前请结合实际招聘信息进行确认", ai=True)
    first_row = st.columns(2)
    with first_row[0]:
        render_result_card("👋", "打招呼语", result["greeting"], "greeting")
    with first_row[1]:
        render_result_card("💼", "工作内容", result["job_description"], "job_description")
    second_row = st.columns(2)
    with second_row[0]:
        render_result_card("💰", "薪资福利", result["salary_benefits"], "salary_benefits")
    with second_row[1]:
        render_result_card("💬", "完整沟通话术", result["full_message"], "full_message", complete=True)
