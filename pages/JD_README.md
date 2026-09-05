# JD 解析模块

启动命令不变：` .\.venv\Scripts\python.exe -m streamlit run app.py`。
侧栏的 **岗位管理** 下分为两个页面：**JD 解析**负责新建岗位；**已保存岗位**负责查看和编辑已有岗位。
此模块不改变首页或其他业务模块。

## 本地解析（默认）

本地解析直接读取粘贴的 JD，不需要 API Key，也不会把内容发送到外部服务。建议填写岗位名称；系统会保守识别学历、经验和明确出现的能力关键词，并生成一份待 HR 复核的能力权重草案。它不是大模型，未识别不代表岗位没有该项要求。

## Mock 模式

在页面手动选择后开启。
无论粘贴什么 JD，均返回固定 Python 工程师测试数据，不进行真实分析。
空 JD 仍会提示错误。保存记录使用 `mode=mock`，请勿当成真实岗位结论。

## 真实 API 模式

使用支持 Chat Completions JSON 模式的 HTTPS 接口。PowerShell 示例：

```powershell
$env:LLM_API_KEY = "你的密钥"
$env:LLM_MODEL = "你有权限使用且支持 JSON 模式的模型 ID"
$env:LLM_BASE_URL = "https://api.openai.com/v1"
.\.venv\Scripts\python.exe -m streamlit run app.py
```

也可替换为其他兼容服务的基础 URL（不含 `/chat/completions`）。
优先读取进程环境变量，其次读取 Streamlit Secrets；不自动读取 `.env`。修改配置后重启服务；勿将真实密钥写入仓库。示例见根目录 `secrets.toml.example`。
真实模式会将 JD 发给配置的服务，需在页面确认授权。失败时展示错误，不自动降级为 Mock。
接口使用 `response_format=json_object`，应用另行严格校验字段和权重。
参考：[OpenAI JSON 模式说明](https://developers.openai.com/api/docs/guides/structured-outputs)。

## JSON 与存储

`job_title`、`education`、`experience` 为字符串；三个 skills 字段为字符串数组。
`competency_model` 为数组，每项包含 `dimension`、`weight`、`description`。
权重为百分比，总和必须为 100；JD 信息不足时允许空数组。缺失文本用“未提及”，缺失技能用空数组。
胜任力模型是待 HR 复核的建议，不用于自动做出录用决定。

成功后自动写入 `database/recruitment.sqlite3` 的 `jd_jobs` 表，包含原 JD、完整 JSON、岗位名称、模式和 UTC 时间。
“编辑已保存岗位”可以载入原始 JD、工作地点和薪资范围，重新解析后覆盖该岗位，同时保留原岗位 ID，供已有匹配报告继续关联。地点和薪资属于岗位信息，不参与能力匹配计分。
数据库路径可通过 `JD_DATABASE_PATH` 更改。相同输入、结果和模式不会重复插入。
数据库为本地明文文件，已由现有 `.gitignore` 排除；请勿粘贴个人信息或敏感资料。

## 验证

` .\.venv\Scripts\python.exe -m pytest -q` 运行全部测试。
JD 测试使用临时 SQLite 和模拟 HTTP，不调用真实 API，也不写入正式数据库。
