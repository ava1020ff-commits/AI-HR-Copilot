"""Streamlit 展示层的统一视觉与侧栏品牌。"""

import streamlit as st


def apply_saas_theme(section: str) -> None:
    """应用克制的企业 HR SaaS 视觉，不修改业务状态。"""
    # 样式通过专用 HTML 通道注入，避免 Markdown 将标签作为正文展示。
    # 仅使用固定样式，不插入用户数据，也不启用 JavaScript。
    st.html(
        """
        <style>
        :root { --hr-ink:#172033; --hr-muted:#667085; --hr-line:#e7eaf0; --hr-accent:#3157a4; }
        .stApp { background:#f8f9fb; color:var(--hr-ink); }
        [data-testid="stHeader"] { background:rgba(248,249,251,.88); }
        [data-testid="stSidebar"] { background:#ffffff; border-right:1px solid var(--hr-line); }
        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p { color:var(--hr-muted); }
        .block-container { max-width:1280px; padding-top:3.25rem; padding-bottom:5rem; }
        h1 { color:var(--hr-ink); letter-spacing:-.035em; font-size:2.35rem !important; margin-bottom:.4rem !important; }
        h2 { color:var(--hr-ink); letter-spacing:-.02em; margin-top:2.3rem !important; }
        h3 { color:#344054; font-size:1.05rem !important; }
        p, label, [data-testid="stCaptionContainer"] { line-height:1.65; }
        [data-testid="stMetric"] { background:#fff; border:1px solid var(--hr-line); border-radius:14px; padding:1.15rem 1.25rem; min-height:112px; box-shadow:0 1px 2px rgba(16,24,40,.03); }
        [data-testid="stMetricLabel"] { color:var(--hr-muted); }
        [data-testid="stMetricValue"] { color:var(--hr-ink); font-weight:650; font-size:2rem; }
        [data-testid="stVerticalBlockBorderWrapper"] { background:#fff; border-color:var(--hr-line) !important; border-radius:14px; }
        [data-testid="stAlert"] { border-radius:12px; }
        .stButton > button, [data-testid="stFormSubmitButton"] > button { border-radius:9px; min-height:2.7rem; font-weight:600; }
        .stButton > button[kind="primary"], [data-testid="stFormSubmitButton"] > button[kind="primary"] { background:var(--hr-accent); border-color:var(--hr-accent); }
        [data-testid="stTextInput"] input, [data-testid="stTextArea"] textarea, [data-baseweb="select"] > div { border-radius:9px; border-color:#d8dde7; background:#fff; }
        [data-testid="stFileUploaderDropzone"] { background:#fff; border-color:#cfd6e3; border-radius:12px; padding:1.25rem; }
        [data-testid="stExpander"] { background:#fff; border:1px solid var(--hr-line); border-radius:10px; }
        [data-testid="stDataFrame"], [data-testid="stTable"] { border:1px solid var(--hr-line); border-radius:10px; overflow:hidden; }
        hr { border-color:var(--hr-line); margin:2rem 0; }
        @media (max-width: 700px) { .block-container { padding-top:2rem; } h1 { font-size:1.9rem !important; } }
        </style>
        """,
    )
    with st.sidebar:
        st.markdown("### AI Recruitment")
        st.caption("Enterprise HR Copilot")
        st.divider()
        st.caption(f"当前模块 · {section}")
