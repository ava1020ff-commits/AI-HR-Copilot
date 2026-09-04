"""环境变量优先，Streamlit Secrets 其次；不记录配置值。"""

import os
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def get_setting(name: str, default: str = "") -> str:
    value = os.environ.get(name)
    if value is None:
        try:
            value = st.secrets.get(name, default)
        except FileNotFoundError:
            value = default
    if not isinstance(value, str):
        raise ValueError(f"配置 {name} 必须为字符串。")
    return value.strip()


def resolve_data_path(value: str) -> Path:
    """相对配置始终以项目根目录为基准，而不是启动终端目录。"""
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path
