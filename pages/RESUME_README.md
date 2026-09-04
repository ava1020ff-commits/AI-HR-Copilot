# 简历解析

从侧栏进入“简历解析”，上传 PDF 或 DOCX，点击“解析简历”。结果显示在可编辑表单中。
修改后勾选人工复核，点击“确认保存”才写入 SQLite。解析、页面刷新、未确认提交均不会入库。
替换或移除上传文件、切换解析模式会清除旧草稿，避免保存错人。

## 支持范围

- PDF：可选中文字的文本版，最大 10 MB、30 页。加密、扫描或包含无文字页面的 PDF 会提示处理后重新上传；不提供 OCR。
- DOCX：正文、表格（包括嵌套表格）、默认页眉页脚。最大 10 MB，解压不超过 30 MB。
- 不提取图片、照片和文档元数据；复杂文本框、修订内容及多栏阅读顺序可能漏项，需要 HR 对照原文核验。
- 无密钥时默认本地规则模式，支持常见中英文章节标题；没有固定示例替换真实内容。缺失信息留空。
- AI 模式沿用 JD 的 `LLM_API_KEY`、`LLM_MODEL`、`LLM_BASE_URL`。必须确认发送授权，未配置或调用失败会报错，不静默降级。

## 标准化与人工修改

`candidate_name` 为字符串，其余 `education`、`work_experience`、`internships`、`projects`、`skills`、`certificates` 均为字符串数组。
数组条目保留原文中的时间、组织、角色等事实；页面每行一条，可自由增删。
统一 Unicode、去空白、去重；缺失字段不推测，保存时姓名不能为空。

## 数据边界

只保存上述七个字段、解析模式、去重指纹和确认时间。原始文件、文件名和提取原文不写入数据库。
默认使用 `database/recruitment.sqlite3` 的 `candidates` 表；可设置 `RESUME_DATABASE_PATH`，否则沿用 `JD_DATABASE_PATH`。
相同标准化结果及模式不会重复保存；修改后再次保存生成新快照，不覆盖旧记录。当前没有候选人合并功能。
SQLite 为本地明文，请限制目录访问权限，不要提交真实简历或数据库。

不建立性别、年龄、照片、婚姻字段；校验拒绝额外字段及常见敏感表述。
`services.resume_parser.matching_fields()` 仅输出六类职业字段，排除姓名。
自动过滤不是完整匿名化保障，HR 仍需移除隐含或漏检的敏感内容；本模块不执行人岗匹配或录用决策。

## 安装与验证

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m streamlit run app.py
```

文本提取参考 [pypdf 文档](https://pypdf.readthedocs.io/en/5.4.0/user/extract-text.html)，
API JSON 校验参考 [OpenAI 文档](https://developers.openai.com/api/docs/guides/structured-outputs)。
# 候选人搜索与筛选

页面下方的“已保存候选人”列表仅展示 HR 已确认的数据。支持按姓名、ID、职业经历和技能搜索；空格分隔的多个关键词需全部匹配，英文忽略大小写。教育记录和技能可叠加筛选，教育记录保留简历原文，不推断学历等级。点击“清空筛选”恢复全部记录，选择候选人可查看职业详情。搜索不会改写数据库、匹配分数或招聘状态，不使用性别、年龄和婚育字段。
