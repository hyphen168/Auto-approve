# Office AI 自动化办公助手

一个支持 **Word / Excel / PPT** 的自动化办公 Web 应用，内置多种 **免费大模型** 接入，适合部署到云服务器使用。

## 核心功能

- **AI 助手对话**：内置多轮对话，可自由扩展为各种办公任务。
- **Word 文档**
  - 根据主题 + 要求一键生成结构完整的 `.docx` 文档
  - 对已有 `.docx` 一键生成中文摘要（可下载）
  - 一键翻译 `.docx` 为多种语言并下载
  - **模板套用**：上传带 `{{姓名}}` 占位符的模板，AI 智能填值或手动填写后下载
- **Excel 表格**
  - 上传 `.xlsx` 进行 AI 数据分析（结构、数据质量、业务建议）
  - 一键把 AI 分析报告写入新工作表下载
  - 按首行表头自动生成 N 条合理数据
  - 一键为数值列生成柱状图 / 折线图
- **PPT 演示**
  - 根据主题 + 页数一键生成带封面和正文的 `.pptx`
  - 对已有 `.pptx` 一键生成内容摘要
- **PDF 转换**：一键把 Word / PPT 转为 PDF（生成时可选同步下载 PDF）
- **批量处理**：一次处理多个 Word / Excel / PPT —— 批量摘要、批量翻译、批量分析、批量转 PDF，打包 ZIP 下载
- **访问登录**：内置单用户密码登录保护所有接口（默认密码 `admin123`，请部署后立即修改）

## 支持的内置免费大模型

在「设置」界面选择即可：

| 提供方 | 费用 | 说明 |
| --- | --- | --- |
| 本地 Ollama | 免费 | 需在服务器上自部署 Ollama，模型如 `qwen2.5:7b` |
| 硅基流动 SiliconFlow | 免费额度 | 需注册获取 API Key，如 `Qwen/Qwen2.5-7B-Instruct` |
| 智谱 GLM-4-Flash | 免费额度 | 需注册获取 API Key，模型 `glm-4-flash` |
| DeepSeek | 低价（非免费） | 需充值获取 API Key |
| 自定义 OpenAI 兼容接口 | 视服务而定 | 任意兼容 OpenAI 的接口 |

> 也可通过环境变量预设：`OFFICE_AI_BASE_URL`、`OFFICE_AI_MODEL`、`OFFICE_AI_API_KEY`、`OFFICE_AI_DATA_DIR`。

## 登录与安全

- 应用默认开启登录保护，初始密码为 **`admin123`**，部署后请在「设置 → 修改访问密码」中立即更换。
- 登录使用 HttpOnly Cookie，除 `/api/login` `/api/logout` `/api/me` 外，所有 `/api/*` 接口均需登录。
- 如确需完全开放访问，可删除 `data/config.json` 中的 `auth_*` 字段或将 `auth_enabled` 设为 `false`。

## 云端部署

### 方式一：Docker（推荐）

在云服务器上执行：

```bash
git clone <你的仓库地址> office-ai-assistant
cd office-ai-assistant
docker compose up -d --build
```

然后访问 `http://<服务器IP>:8000`，使用初始密码 `admin123` 登录，在「设置」界面配置大模型即可使用。

> Docker 镜像已内置 LibreOffice 和中文字体，Word/PPT 转 PDF 开箱即用。

### 方式二：手动安装运行

```bash
cd office-ai-assistant
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# 安装 LibreOffice（用于 Word/PPT 转 PDF，Ubuntu）
sudo apt-get update && sudo apt-get install -y libreoffice-writer libreoffice-impress
# 设置大模型（可选，也可网页里配置）
export OFFICE_AI_API_KEY=你的key
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 方式三：云 PaaS 平台

本应用是标准 FastAPI 服务，可部署到任意支持 Python/Docker 的 PaaS：
阿里云函数计算、腾讯云、Vultr、Render、Railway、Fly.io 等，均从 `run.py` 或 `Dockerfile` 启动。

## 本地开发运行

```bash
pip install -r requirements.txt
python run.py        # 或 uvicorn app.main:app --reload
# 浏览器打开 http://localhost:8000
```

## API 一览

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/api/login` | 登录 |
| POST | `/api/logout` | 退出登录 |
| GET | `/api/me` | 当前登录状态 |
| POST | `/api/password` | 修改登录密码 |
| GET | `/api/settings` | 读取配置 |
| POST | `/api/settings` | 保存配置 |
| POST | `/api/test` | 测试大模型连接 |
| POST | `/api/chat` | AI 多轮对话 |
| POST | `/api/word/generate` | 生成 Word（可选同时转 PDF） |
| POST | `/api/word/summarize` | Word 摘要 |
| POST | `/api/word/translate` | Word 翻译 |
| POST | `/api/pdf/convert` | Word/PPT 转 PDF |
| POST | `/api/template/fields` | 识别模板占位符 |
| POST | `/api/template/ai-suggest` | 模板 AI 智能填值 |
| POST | `/api/template/fill` | 填充模板并下载 |
| POST | `/api/excel/info` | 读取工作表名 |
| POST | `/api/excel/analyze` | Excel 分析 |
| POST | `/api/excel/report` | 写入分析报告 |
| POST | `/api/excel/generate-rows` | 生成数据行 |
| POST | `/api/excel/chart` | 生成图表 |
| POST | `/api/ppt/generate` | 生成 PPT（可选同时转 PDF） |
| POST | `/api/ppt/summarize` | PPT 摘要 |
| POST | `/api/batch` | 批量处理并打包下载 |

## 项目结构

```
office-ai-assistant/
├── app/
│   ├── main.py          # FastAPI 接口（含登录中间件）
│   ├── auth.py          # 登录鉴权
│   ├── config.py        # 大模型与鉴权配置
│   ├── llm.py           # 调用免费大模型
│   ├── md_parse.py      # 解析 AI 输出的 Markdown
│   ├── word_ops.py      # Word 生成/摘要/翻译
│   ├── template_ops.py  # Word 模板占位符填充
│   ├── excel_ops.py     # Excel 分析/生成数据/图表
│   ├── ppt_ops.py       # PPT 生成/摘要
│   ├── pdf_ops.py       # Word/PPT 转 PDF（LibreOffice）
│   ├── batch_ops.py     # 批量处理打包
│   └── static/          # 前端界面
├── run.py
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── README.md
```

## 上传到 GitHub

```bash
cd office-ai-assistant
git init
git add .
git commit -m "Initial commit: Office AI assistant"
git branch -M main
git remote add origin https://github.com/<你的用户名>/<仓库名>.git
git push -u origin main
```

> 若你希望我代为推送，请告诉我你的 GitHub 用户名、仓库名，并准备好认证方式（如 `gh auth login` 或个人访问令牌）。

## 免责声明

使用第三方免费大模型接口请遵守其服务条款和用量限制。本工具仅作办公辅助用途，生成内容仅供参考，重要文件请人工复核。