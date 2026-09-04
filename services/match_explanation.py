"""Shared score explanation for demo and matching reports."""

import streamlit as st

EVIDENCE_NOTICE = "证据来自候选人自述，尚未外部核验。规则可复现不等于已经证明评分有效；分数不是实际能力或录用概率。"


def render_dimension(dimension: dict) -> None:
    """Explain the stored scoring snapshot without recalculating it."""
    st.text("岗位要求：" + dimension.get("requirement", "旧快照未保存岗位要求，请重新计算。"))
    st.text(f"权重：{dimension['max_score']:g}%（满分 {dimension['max_score']:g} 分）")
    criteria = dimension["criteria"]
    for criterion in criteria:
        st.text("评分指标：" + criterion["criterion"])
        sources = criterion.get("evidence_sources", [])
        for evidence in sources:
            st.text(f"原文证据：{evidence['quote']}（{evidence['source']}）")
        if not sources:
            st.text("原文证据：暂无可定位引用；旧快照请重新计算。" if "evidence_sources" not in criterion else "原文证据：暂无明确证据。")
        level = criterion["attainment"]
        label = {1: "实践经历或学历达标的自述", 0.5: "技能栏自述，缺少实践佐证", 0: "未识别到支持证据"}[level]
        st.text("证据类型：" + label)
        st.text(f"计分规则：维度权重 {dimension['max_score']:g} ÷ {len(criteria)} 个指标 × 系数 {level:g}；各指标相加后四舍五入至两位小数。")
        if level == 1:
            verify = "核验经历真实性、个人贡献和实际产出；学历类核验相应证明。满系数仅表示命中规则，不表示能力已获验证。"
        elif level == 0.5:
            verify = "请提供使用该技能的具体项目、个人任务和可核验成果。"
        else:
            verify = "请补充相关经历或作品；没有证据不等于没有能力。"
        st.text("待核实内容：" + verify)
    if not criteria:
        st.text("原文证据：暂无明确证据。")
        st.text("证据类型：评分口径未明确。")
        st.text("待核实内容：先明确岗位评价指标，再补充相关证据。")
    st.text("维度合计计分规则：" + dimension["reason"])
    st.caption(EVIDENCE_NOTICE)
