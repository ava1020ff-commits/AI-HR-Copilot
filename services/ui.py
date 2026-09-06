"""人力工作台的统一展示组件；不读取或修改业务数据。"""

from html import escape
from pathlib import Path

import streamlit as st

NAVIGATION_GROUPS = (
    ("首页", (("app.py", "▦  首页", "首页"),)),
    ("招聘管理", (
        ("pages/07_已保存岗位.py", "▣  岗位", "已保存岗位"),
        ("pages/02_候选人.py", "♙  候选人", "候选人"),
        ("pages/03_智能匹配.py", "✦  智能匹配", "智能匹配"),
        ("pages/04_面试助手.py", "◉  面试", "面试助手"),
        ("pages/06_候选人寻访.py", "⌕  人才寻访", "候选人寻访"),
        ("pages/05_招聘分析.py", "▥  招聘分析", "招聘分析"),
    )),
    ("人力分析", (
        ("pages/11_人员异动.py", "↔  人员异动", "人员异动"),
        ("pages/12_人力成本.py", "▤  人力成本", "人力成本"),
    )),
)
MOBILE_NAVIGATION = tuple(item for _, group in NAVIGATION_GROUPS for item in group) + (("pages/01_岗位管理.py", "＋  创建岗位", "JD 解析"),)


def mode_label(mode: str) -> str:
    """Translate persisted technical mode identifiers for workflow labels."""
    return {"mock": "示例模式", "local": "本地解析", "llm": "智能解析"}.get(mode, "未知模式")


def apply_saas_theme(section: str) -> None:
    """应用企业招聘 SaaS 视觉和分组导航，不修改业务状态。"""
    st.html(Path(__file__).with_name("theme.css"))
    with st.container(key="mobile_menu"):
        with st.popover("菜单", use_container_width=True):
            st.caption(f"当前位置：{section}")
            for path, label, _ in MOBILE_NAVIGATION:
                st.page_link(path, label=label)
    with st.sidebar:
        with st.container(key="brand"):
            st.markdown("### FF 人力工作台")
            st.caption("People Workspace")
        for group_name, items in NAVIGATION_GROUPS:
            if group_name != "首页":
                st.caption(group_name)
            for path, label, section_name in items:
                active = section_name == section or (section == "首页" and path == "app.py")
                level = "subnav" if group_name != "首页" else "nav"
                state = "active" if active else "item"
                with st.container(key=f"{level}_{state}_{Path(path).stem}"):
                    st.page_link(path, label=label)


def render_page_header(title: str, subtitle: str, *, action_path: str | None = None, action_label: str | None = None) -> None:
    """统一页面标题，并可在右侧放置一个主操作。"""
    left, right = st.columns([4, 1])
    with left:
        st.title(title)
        if subtitle:
            st.caption(subtitle)
    if action_path and action_label:
        with right:
            with st.container(key="page_primary_action"):
                st.page_link(action_path, label=action_label, use_container_width=True)


def render_section_title(title: str, subtitle: str = "", *, ai: bool = False) -> None:
    st.subheader(("✦ " if ai else "") + title)
    if subtitle:
        st.caption(subtitle)


def render_empty_state(icon: str, title: str, description: str, *, action_path: str | None = None, action_label: str | None = None) -> None:
    """用结构化空状态替代大面积提示框。"""
    state_key = "empty_state_" + "_".join(title.split())
    with st.container(border=True, key=state_key):
        st.markdown(f"<div class='hm-empty-icon'>{escape(icon)}</div>", unsafe_allow_html=True)
        st.markdown(f"### {escape(title)}")
        st.caption(description)
        if action_path and action_label:
            with st.container(key=f"empty_primary_action_{state_key}"):
                st.page_link(action_path, label=action_label)


def render_tags(items: list[str], *, empty_text: str = "未提及") -> None:
    if not items:
        st.caption(empty_text)
        return
    markup = "".join(f"<span class='hm-tag'>{escape(str(item))}</span>" for item in items)
    st.markdown(f"<div class='hm-tags'>{markup}</div>", unsafe_allow_html=True)


def render_ai_intro(title: str, description: str) -> None:
    with st.container(border=True, key="ai_intro"):
        st.markdown(f"### ✦ {escape(title)}")
        st.caption(description)
