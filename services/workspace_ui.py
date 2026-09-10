"""首页工作驾驶舱组件。"""

import streamlit as st


def render_global_search() -> str:
    return st.text_input("全局搜索", placeholder="搜索岗位、候选人、招聘任务……", label_visibility="collapsed", key="workspace_search")


def render_recruitment_metrics(metrics: tuple[dict, ...]) -> None:
    with st.container(key="workspace_metrics"):
        for column, item in zip(st.columns(4), metrics):
            with column, st.container(border=True, key=f"status_{item['tone']}"):
                st.caption("●  " + item["label"])
                st.markdown(f"## {item['value']}")
                st.caption(item["detail"])


def render_ai_recruiting_summary(items: tuple[tuple[str, str], ...]) -> None:
    with st.container(border=True, key="workspace_ai"):
        left, right = st.columns([4, 1], vertical_alignment="center")
        left.markdown("### ✦ AI 招聘助手")
        left.caption("让 AI 帮你处理重复性招聘工作 · 今日演示摘要")
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
        st.info("没有找到匹配的招聘任务。" if query else "今天没有待处理任务 🎉")
    elif view == "列表":
        st.dataframe([{"状态": t["status"], "任务": t["type"], "岗位": t["job"], "内容": t["summary"], "下一步": t["next"], "截止时间": t["due"]} for t in filtered], hide_index=True, width="stretch")
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
