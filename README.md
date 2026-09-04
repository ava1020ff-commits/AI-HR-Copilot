# AI Recruitment Copilot

简历模块已支持 PDF/DOCX 上传、解析、人工修改和确认保存。首次使用请重新安装
`requirements.txt` 中的依赖，详见 [简历模块说明](pages/RESUME_README.md)。
JD 模块详见 [JD 模块说明](pages/JD_README.md)。云部署见 [部署指南](DEPLOYMENT.md)。

人岗匹配模块支持选择已保存岗位和候选人，按能力模型逐维度计算证据分；
不调用 LLM 生成总分，不自动淘汰。评分口径和限制见 [人岗匹配说明](pages/MATCHING_README.md)。

面试助手按 JD、能力模型、候选人经历和匹配报告生成四类可追溯问题，见 [面试助手说明](pages/INTERVIEW_README.md)。

Recruitment Dashboard 使用 Plotly 展示匹配分析和人工记录的招聘漏斗，统计口径见 [Dashboard 说明](pages/DASHBOARD_README.md)。

Python + Streamlit 招聘助手，包含岗位、候选人、匹配、面试和招聘分析页面。公网部署目前仅适合虚构数据演示：没有登录与用户隔离，所有访客共享 SQLite 数据；云端本地文件不保证持久保存。

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
pages/              五个功能页面
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

测试通过 Streamlit AppTest 验证六个页面，并覆盖解析、保存、评分、面试问题与图表数据。
目前没有独立构建步骤、覆盖率门槛或格式化工具。
直接依赖已固定为本地验证版本；GitHub Actions 使用 Ubuntu + Python 3.12 回归测试。

## 数据与配置

不要提交真实候选人资料、API 密钥或数据库文件。无需密钥即可使用 JD Mock 和简历本地解析。配置优先级为环境变量、Streamlit Secrets、默认值；不自动加载 `.env`。复制 `secrets.toml.example` 为 `.streamlit/secrets.toml` 可配置本地密钥，真实文件已被 Git 忽略。
