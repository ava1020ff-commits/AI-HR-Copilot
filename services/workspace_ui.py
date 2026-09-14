"""首页工作驾驶舱组件。"""

from html import escape
from pathlib import Path

import streamlit as st

from services.ui import render_data_table, render_status


def render_global_search() -> str:
    return st.text_input("全局搜索", placeholder="搜索岗位、候选人、招聘任务……", label_visibility="collapsed", key="workspace_search")


def render_recruitment_metrics(metrics: tuple[dict, ...]) -> None:
    with st.container(border=True, key="workspace_metrics"):
        for column, item in zip(st.columns(4), metrics):
            with column, st.container(border=False, key=f"status_{item['tone']}"):
                st.caption(item["label"], help=item["detail"])
                st.markdown(f"## {item['value']}")


def render_ai_recruiting_summary(items: tuple[tuple[str, str], ...]) -> None:
    with st.container(border=True, key="workspace_ai"):
        left, right = st.columns([4, 1], vertical_alignment="center")
        left.markdown("### ✦ AI 招聘助手")
        left.caption("让 AI 帮你处理重复性招聘工作 · 今日操作摘要")
        right.page_link("pages/05_招聘分析.py", label="查看 AI 报告", use_container_width=True)
        for column, (label, value) in zip(st.columns(5), items):
            column.markdown(f"**{value}**")
            column.caption(label)
        with st.expander("开始 AI 招聘", expanded=False):
            st.text_area("描述任务", placeholder="输入岗位 JD、候选人信息，或描述你现在需要处理的招聘任务……", label_visibility="collapsed")
            actions = (("AI 筛选简历", "pages/03_智能匹配.py"), ("生成 BOSS 沟通话术", "pages/08_BOSS沟通话术.py"), ("生成面试题", "pages/04_面试助手.py"), ("分析候选人", "pages/02_候选人.py"), ("优化 JD", "pages/01_岗位管理.py"))
            for column, (label, path) in zip(st.columns(5), actions):
                column.page_link(path, label=label, use_container_width=True)


def render_task_card(task: dict, index: int) -> None:
    with st.container(border=True, key=f"task_{task['status']}_{task['tone']}_{index}"):
        st.caption(task["type"])
        st.markdown(f"### {task['job']}")
        st.write(task["summary"])
        st.divider()
        st.caption("当前状态")
        st.write(task["state"])
        st.caption("下一步")
        st.write(task["next"])
        meta = st.columns(2)
        meta[0].caption("负责人 · " + task["owner"])
        meta[1].caption("截止 · " + task["due"])
        st.page_link(task["path"], label=task["action"] + " →", use_container_width=True)


def render_recruitment_board(tasks: tuple[dict, ...], query: str) -> None:
    heading, switch = st.columns([4, 1], vertical_alignment="center")
    heading.subheader("我的招聘工作")
    view = switch.radio("视图", ("看板", "列表"), horizontal=True, label_visibility="collapsed")
    filtered = [task for task in tasks if not query or query.lower() in " ".join(str(value) for value in task.values()).lower()]
    if not filtered:
        st.info("没有找到匹配的招聘任务。" if query else "今天没有待处理任务。")
    elif view == "列表":
        render_data_table([{"状态": t["status"], "任务": t["type"], "岗位": t["job"], "内容": t["summary"], "下一步": t["next"], "截止时间": t["due"]} for t in filtered], hide_index=True, width="stretch")
    else:
        for column, status in zip(st.columns(3), ("待处理", "进行中", "已完成")):
            scoped = [task for task in filtered if task["status"] == status]
            column.markdown(f"### {status}  {len(scoped)}")
            with column:
                for index, task in enumerate(scoped):
                    render_task_card(task, index)


def render_today_schedule(items: tuple[dict, ...]) -> None:
    st.subheader("今日招聘日程")
    if not items:
        st.info("暂无面试日程。")
        return
    with st.container(border=True, key="workspace_schedule"):
        for item in items:
            time, content, action = st.columns([1, 4, 2], vertical_alignment="center")
            time.markdown(f"**{item['time']}**")
            content.markdown(f"**{item['title']}**")
            content.caption(item["detail"])
            action.page_link(item["path"], label=item["action"] + " →")


def render_recruitment_alerts(items: tuple[dict, ...]) -> None:
    st.subheader("招聘预警")
    if not items:
        st.info("当前没有需要处理的招聘预警。")
        return
    with st.container(border=True, key="workspace_alerts"):
        for item in items:
            content, action = st.columns([4, 2], vertical_alignment="center")
            content.markdown(f"<span class='hm-alert-dot {item['level']}'></span><strong>{item['title']}</strong>", unsafe_allow_html=True)
            content.caption(item["detail"])
            action.page_link(item["path"], label=item["action"] + " →")


def render_action_queue(actions: tuple[dict, ...]) -> None:
    """One work surface for action rows, searchable details and definitions."""
    with st.container(key="workspace_tasks_section"):
        st.subheader("需要我处理")
        with st.container(border=True, key="workspace_actions"):
            with st.container(key="workspace_action_head"):
                for column, heading in zip(st.columns([5, 2, 1, 2]), ("任务", "状态", "数量", "操作")):
                    column.caption(heading)
            for item in actions:
                with st.container(key=f"workspace_action_row_{item['key']}"):
                    label, status, count, action = st.columns([5, 2, 1, 2], vertical_alignment="center")
                    label.markdown(f"**{item['label']}**", help=item["detail"])
                    available = item.get("available", True)
                    with status:
                        render_status("未接入" if not available else "待处理" if item["value"] else "暂无待办",
                                      "info" if available and item["value"] else "neutral")
                    count.markdown(f"**{item['value'] if available else '—'}**")
                    action.page_link(item["path"], label=item["action"], use_container_width=True)
            with st.expander("查看待办明细", expanded=False):
                query = st.text_input("搜索待办", placeholder="搜索候选人或岗位", key="workspace_search").strip().lower()
                records = [{"待办": item["label"], **row} for item in actions for row in item["rows"]]
                records = [row for row in records if not query or query in " ".join(str(value) for value in row.values()).lower()]
                if records:
                    render_data_table(records)
                else:
                    st.caption("没有找到匹配的待办。" if query else "暂无可列出的待办明细。")
            with st.expander("统计口径与数据说明", expanded=False):
                summary = "跟进与Offer待办按人岗组合计数；同一候选人可能涉及多个岗位。未接入的数据不显示为零待办。"
                items = "".join(
                    '<div class="metrics-definition-item">'
                    f'<span class="metrics-definition-label">{escape(str(item["label"]))}：</span>'
                    f'<span class="metrics-definition-text">{escape(str(item["detail"]))}</span></div>'
                    for item in actions
                )
                st.markdown(
                    '<div class="metrics-definition">'
                    f'<div class="metrics-definition-summary">{escape(summary)}</div>'
                    f'<div class="metrics-definition-items">{items}</div></div>',
                    unsafe_allow_html=True,
                )


def render_job_progress(rows: tuple[dict, ...]) -> None:
    from services.ui import render_empty_state

    with st.container(key="workspace_progress_section"):
        st.subheader("招聘进展")
        st.caption("岗位进展 · 当前阶段快照，不代表完整招聘漏斗或转化率。")
        if rows:
            render_data_table(list(rows))
        else:
            render_empty_state("▥", "暂无岗位进展", "创建岗位并保存候选人匹配记录后，可在这里查看招聘进展。",
                               action_path="pages/01_岗位管理.py", action_label="创建岗位")


def render_ai_tools() -> None:
    with st.container(key="workspace_tools_section"):
        st.subheader("AI 助手")
        tools = (
            ("JD分析", "解析岗位要求与能力模型", "pages/01_岗位管理.py"),
            ("简历匹配", "对照岗位查看候选人匹配情况", "pages/03_智能匹配.py"),
            ("面试题生成", "生成结构化面试问题", "pages/04_面试助手.py"),
            ("BOSS沟通话术", "准备候选人沟通内容", "pages/08_BOSS沟通话术.py"),
        )
        with st.container(border=False, key="workspace_ai_tools"):
            icons = ("description", "person_search", "quiz", "chat")
            for column, (label, description, path), icon in zip(st.columns(4), tools, icons):
                column.page_link(path, label=label, icon=f":material/{icon}:", use_container_width=True)
                column.caption(description)


def apply_workspace_layout() -> None:
    """Load homepage-scoped presentation while inheriting global design tokens."""
    st.html(Path(__file__).with_name("workspace.css"))
