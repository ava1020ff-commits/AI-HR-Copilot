# FF 人力工作台

People Workspace：连接招聘管理与人力分析的一体化工作台。

当前已完整实现招聘管理流程；人力分析包含人员异动跟进，以及人力成本指标的核算、复核和周报流程。

[在线体验](https://ff-hr-workbench.streamlit.app/) · [源代码](https://github.com/ava1020ff-commits/AI-HR-Copilot) · [部署指南](DEPLOYMENT.md)

## 60 秒体验

1. 打开首页的「首次访问？查看虚构案例」，点击「查看示例匹配」。无需 API Key 或上传文件。
2. 查看产品能力的实践证据、AI 应用的技能自述，以及数据能力的信息缺口。
3. 查看待核实项与推荐面试问题，了解如何把简历线索转化为人工核实任务。

案例完全虚构，使用实际匹配规则计算，不写入数据库、不影响工作台统计。示例分数不是模型准确率或录用概率。

## 项目亮点与边界

- 逐维度展示得分、指标与结构化简历引用，保留可追溯来源。
- 区分实践证据、技能自述和信息不足，不把缺失信息直接解释为能力不足。
- JD 解析与已保存岗位分开管理，并与候选人搜索、合规寻访、面试准备和分析页面组成完整演示流程。
- 寻访页从岗位生成职业搜索词，跳转 BOSS 直聘或猎聘，并通过 CSV 模板人工确认导入；不模拟登录、不抓取、不自动联系。
- 匹配总分使用确定性规则，不由大模型直接评分；不自动淘汰候选人。
- 当前为演示原型，没有登录、用户隔离和持久化云数据库，不应上传真实简历。

分享时建议将链接文字写作「FF 人力工作台｜在线体验」，源码链接写作「项目说明与源码」。在线地址为 https://ff-hr-workbench.streamlit.app/ 。

简历模块已支持 PDF/DOCX 上传、解析、人工修改和确认保存。首次使用请重新安装
`requirements.txt` 中的依赖，详见 [简历模块说明](pages/RESUME_README.md)。
JD 模块详见 [JD 模块说明](pages/JD_README.md)。云部署见 [部署指南](DEPLOYMENT.md)。

人岗匹配模块支持选择已保存岗位和候选人，按能力模型逐维度计算证据分；
不调用 LLM 生成总分，不自动淘汰。评分口径和限制见 [人岗匹配说明](pages/MATCHING_README.md)。

面试助手按 JD、能力模型、候选人经历和匹配报告生成四类可追溯问题，见 [面试助手说明](pages/INTERVIEW_README.md)。

Recruitment Dashboard 使用 Plotly 展示匹配分析和人工记录的招聘漏斗，统计口径见 [Dashboard 说明](pages/DASHBOARD_README.md)。

Python + Streamlit 人力工作台，包含首页、招聘管理和人力分析。公网部署目前仅适合虚构数据演示：没有登录与用户隔离，所有访客共享 SQLite 数据；云端本地文件不保证持久保存。

## 本地启动

建议使用 Python 3.11 或 3.12。在项目根目录运行以下 PowerShell 命令：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

打开 http://127.0.0.1:8501；在启动终端按 `Ctrl+C` 停止服务。
无需激活虚拟环境。如果系统找不到 `python`，请安装 Python 并加入 PATH，或将第一条命令中的 `python` 替换为已有解释器的完整路径。

## 目录结构

```text
app.py              首页入口
pages/              招聘功能页与人力模块页面
services/           业务服务、配置读取与 AI 集成
database/           SQLite 数据访问层
tests/              自动化测试
.streamlit/          本地运行与主题配置
requirements.txt    运行与测试依赖
AGENTS.md           贡献与协作指南
```

## 验证

```powershell
.\.venv\Scripts\python.exe -m pytest -q
git diff --check
```

测试通过 Streamlit AppTest 验证全部页面，并覆盖解析、保存、评分、面试问题与图表数据。
目前没有独立构建步骤、覆盖率门槛或格式化工具。
直接依赖已固定为本地验证版本；GitHub Actions 使用 Ubuntu + Python 3.12 回归测试。

## 数据与配置

不要提交真实候选人资料、API 密钥或数据库文件。无需密钥即可使用 JD Mock 和简历本地解析。配置优先级为环境变量、Streamlit Secrets、默认值；不自动加载 `.env`。复制 `secrets.toml.example` 为 `.streamlit/secrets.toml` 可配置本地密钥，真实文件已被 Git 忽略。
