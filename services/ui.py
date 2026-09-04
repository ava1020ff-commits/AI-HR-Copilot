"""Streamlit 展示层的统一视觉与侧栏品牌。"""

from pathlib import Path

import streamlit as st

NAVIGATION = (
    ("app.py", "招聘工作台"),
    ("pages/01_岗位管理.py", "岗位管理"),
    ("pages/02_候选人.py", "候选人"),
    ("pages/03_智能匹配.py", "智能匹配"),
    ("pages/04_面试助手.py", "面试助手"),
    ("pages/05_招聘分析.py", "招聘分析"),
)


def mode_label(mode: str) -> str:
    """Translate persisted technical mode identifiers for workflow labels."""
    return {"mock": "示例模式", "local": "本地解析", "llm": "智能解析"}.get(mode, "未知模式")


def apply_saas_theme(section: str) -> None:
    """应用克制的企业 HR SaaS 视觉，不修改业务状态。"""
    # 样式通过专用 HTML 通道注入，避免 Markdown 将标签作为正文展示。
    # 仅使用固定样式，不插入用户数据，也不启用 JavaScript。
    st.html(Path(__file__).with_name("theme.css"))
    with st.container(key="mobile_menu"):
        with st.popover("菜单", use_container_width=True):
            st.caption(f"当前位置：{section}")
            for path, label in NAVIGATION:
                st.page_link(path, label=label)
    with st.sidebar:
        st.markdown("### AI Recruitment")
        st.caption("AI 招聘辅助原型")
        for path, label in NAVIGATION:
            active = label == section or (section == "首页" and path == "app.py")
            with st.container(key=f"nav_{'active' if active else 'item'}_{Path(path).stem}"):
                st.page_link(path, label=label)
        st.divider()
        st.caption(f"当前模块 · {section}")
