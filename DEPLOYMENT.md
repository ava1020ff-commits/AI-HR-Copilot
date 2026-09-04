# Streamlit Community Cloud 部署指南

## 部署范围与限制

入口为根目录 `app.py`，选择 Python 3.12。运行依赖均在 `requirements.txt`；SQLite 使用 Python 标准库，PDF/DOCX 提取不需要操作系统命令或额外 `packages.txt`。扫描版 PDF 暂不支持 OCR。

当前仅适合虚构数据演示：没有登录、租户隔离或调用限流；公开页面的访客共享岗位和候选人数据，也可能消耗配置的 API 额度。不要上传真实简历。生产使用前必须另行增加访问控制、持久数据库和数据合规措施。

Community Cloud 不保证本地文件持久性，SQLite 可能随实例重建丢失。更换本地路径不能解决这个限制。数据库不会上传 GitHub，云端首次启动是空数据。

## 上传 GitHub

1. 在 GitHub 创建空仓库，不预先生成 README。公开仓库的全部代码可被访问；提交前检查内容。
2. 在项目根目录执行（当前项目已初始化 Git，无需重复 init）：

```sh
git status --short
git check-ignore .env .streamlit/secrets.toml .venv/example database/recruitment.sqlite3
git add .
git diff --cached --stat
git diff --cached --check
git diff --cached --name-only
```

3. 仔细检查暂存文件，不应出现密钥、数据库或真实简历；`.gitignore` 不能检测源码中粘贴的 API Key，也不能清除已提交的秘密。误提交的密钥必须撤销并清理历史。
4. 确认后执行（替换 USERNAME；如已有 origin，先检查，不重复添加）：

```sh
git commit -m "Prepare Streamlit cloud deployment"
git branch -M main
git remote add origin https://github.com/USERNAME/AI-HR-Copilot.git
git push -u origin main
```

5. 检查 GitHub Actions 的 Linux tests 是否通过；本地 Windows 测试不等于实际 Linux 验证。

## 创建云应用

1. 登录 https://share.streamlit.io/ 并连接 GitHub。
2. 选择 Create app，选择仓库、`main` 分支，Main file path 填 `app.py`。
3. Advanced settings 选择 Python 3.12。演示模式可不填写 Secrets；真实模式将示例配置粘贴到 Secrets，在线填写密钥，不提交到 Git。
4. 点击 Deploy，查看构建和运行日志。成功后打开生成的 `.streamlit.app` 链接。
5. 使用虚构 JD 和简历依次验证：主页 → JD Mock 解析保存 → PDF/DOCX 本地解析、修改与确认 → 人岗匹配 → 面试问题 → Dashboard 与人工阶段记录。真实 LLM 模式另需验证模型权限、网络与 JSON 返回格式。

## Secrets / 环境变量

根目录 `secrets.toml.example` 不含真实凭据。本地复制到 `.streamlit/secrets.toml`；云端只粘贴其内容到 Secrets 设置。优先读取环境变量（包括显式空字符串），其次读取 `st.secrets`；修改后重启应用。不会自动读取 `.env`。

| 配置 | 是否必需 | 说明 |
| --- | --- | --- |
| `LLM_API_KEY` | 真实 AI 模式必需 | 留空使用 JD Mock／简历本地解析 |
| `LLM_MODEL` | 真实 AI 模式必需 | 有权限且支持 Chat Completions JSON 模式的模型 ID |
| `LLM_BASE_URL` | 可选 | 默认 `https://api.openai.com/v1`；兼容服务必须使用 HTTPS |
| `JD_DATABASE_PATH` | 可选 | 默认 `database/recruitment.sqlite3`，岗位、匹配、阶段数据 |
| `RESUME_DATABASE_PATH` | 可选 | 默认复用 JD 数据库，建议不单独配置 |

路径采用 `/`，相对路径基于项目根目录，不依赖运行终端目录；不需要电脑绝对路径。目录在首次写入时创建。数据库、临时日志、上传目录和 Secrets 已被忽略。不要取消 Streamlit 默认 CORS/XSRF 保护。

## 本地验证

```sh
python -m pip install -r requirements.txt
python -m pip check
python -m pytest -q
python -m streamlit run app.py
```

Windows 未激活环境时将 `python` 换为 `.\.venv\Scripts\python.exe`；Linux 可使用 `.venv/bin/python`。测试使用虚构数据和模拟 API，不验证真实模型的服务可用性。

参考：[官方部署步骤](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy)、[Secrets 管理](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management)、[本地存储限制](https://docs.streamlit.io/develop/concepts/connections/connecting-to-data)。
