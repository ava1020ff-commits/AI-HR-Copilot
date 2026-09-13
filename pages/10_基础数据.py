"""统一维护人力分析使用的基础数据。"""

import sqlite3
from datetime import date

import streamlit as st

from database.hr_base_data import load_base_data, save_base_data
from services.human_cost import ACTIVE_COLUMNS, DEPARTED_COLUMNS, HC_COLUMNS, calculate_dashboard, csv_template, read_csv
from services.ui import apply_saas_theme, render_page_header, render_section_title

st.set_page_config(page_title="基础数据", page_icon="▦", layout="wide")
apply_saas_theme("基础数据")
render_page_header("基础数据", "统一维护人力分析使用的在职人员、离职人员和 HC 数据")
st.info("上传内容包含人事信息，请先脱敏并确认访问权限。三份数据校验通过后将一起更新，人员异动和人力成本页面会自动读取最新版本。")
if st.session_state.pop("base_data_saved", False):
    st.success("基础数据已更新，人员异动和人力成本分析已同步。")

try:
    current = load_base_data()
except (sqlite3.Error, OSError, ValueError):
    current = {"active": [], "departed": [], "hc": [], "updated_at": None}
    st.error("当前基础数据无法读取，请重新上传。")

if current["updated_at"]:
    st.caption(f"当前版本更新时间：{current['updated_at']} · 在职 {len(current['active'])} 人 · 离职 {len(current['departed'])} 人 · HC {len(current['hc'])} 行")

render_section_title("准备数据")
sources = (
    ("在职人员", "人员、序列、合同与近期绩效", ACTIVE_COLUMNS, "active-employees.csv", "active"),
    ("离职人员", "本期离职人员及离职类型", DEPARTED_COLUMNS, "departed-employees.csv", "departed"),
    ("HC", "部门、属地及 M/P/S/O 计划人数", HC_COLUMNS, "headcount.csv", "hc"),
)
uploads = {}
for column, (title, description, fields, filename, key) in zip(st.columns(3), sources):
    with column, st.container(border=True, key=f"base_data_card_{key}"):
        st.markdown(f"### {title}")
        st.caption(description)
        st.download_button("下载模板", csv_template(fields), filename, "text/csv", use_container_width=True, key=f"base_template_{key}")
        uploads[key] = st.file_uploader(f"上传{title}", type=["csv"], key=f"base_upload_{key}", label_visibility="collapsed")

if st.button("保存并更新分析", type="primary", use_container_width=True):
    if not all(uploads.values()):
        st.warning("请同时上传在职人员、离职人员和 HC 三份数据。")
    else:
        try:
            datasets = {
                "active": read_csv(uploads["active"].getvalue(), ACTIVE_COLUMNS),
                "departed": read_csv(uploads["departed"].getvalue(), DEPARTED_COLUMNS),
                "hc": read_csv(uploads["hc"].getvalue(), HC_COLUMNS),
            }
            calculate_dashboard(datasets["active"], datasets["departed"], datasets["hc"], as_of=date.today())
            save_base_data(datasets)
            st.session_state["base_data_version"] = st.session_state.get("base_data_version", 0) + 1
            st.session_state["base_data_saved"] = True
            st.rerun()
        except UnicodeDecodeError:
            st.error("文件编码无法识别，请使用下载模板并保存为 CSV UTF-8 格式。")
        except ValueError as exc:
            st.error(f"数据校验失败：{exc}")
        except (sqlite3.Error, OSError):
            st.error("基础数据保存失败，请稍后重新尝试。")
