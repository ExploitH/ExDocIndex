# 📚 ExDocIndex - 智能文档索引生成系统

<div align="center">

**基于 AI 的文档自动理解与索引构建平台**

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![LLM](https://img.shields.io/badge/LLM-Qwen%2FDeepSeek-orange.svg)](https://dashscope.aliyun.com/)

[功能特性](#-功能特性) • [快速开始](#-快速开始) • [项目结构](#-项目结构) • [使用文档](#-使用文档) • [API 配置](#-api-配置)

</div>

---

## 📖 项目简介

ExDocIndex 是一个智能文档索引生成系统，能够自动理解 PDF、HTML、Markdown、TXT 等多种格式的文档内容，生成结构化的 Markdown 摘要和高密度的 JSON 索引。

系统采用模块化设计，包含以下核心组件：

- **📄 文档解析器** - 支持多种格式的文档解析与 OCR 识别
- **🤖 AI 语义理解** - 基于大语言模型自动提取文档核心信息
- **📊 索引生成器** - 生成适合向量检索的结构化索引
- **🔌 MCP 服务** - 提供标准化的工具调用接口
- **🌐 Web 管理系统** - 可视化的文件管理与任务监控平台

---

## ✨ 功能特性

### 核心能力

| 功能 | 描述 |
|------|------|
| 📁 **多格式支持** | PDF、HTML、Markdown、TXT 文档解析 |
| 🧠 **AI 理解** | 使用 Qwen/DeepSeek 等模型自动理解文档内容 |
| 📝 **智能摘要** | 生成结构化的 Markdown 格式摘要 |
| 🗂️ **索引构建** | 创建高密度 JSON 索引，支持向量检索 |
| 🔌 **MCP 协议** | 兼容 Model Context Protocol 标准 |
| 🌐 **Web 界面** | 现代化的文件管理与任务监控系统 |

### 技术亮点

- ✅ **OCR 增强** - PDF 文档支持 OCR 识别与错别字自动修正
- ✅ **语义解析** - HTML 智能转换为结构化 Markdown
- ✅ **强关联约束** - 源文件与理解结果自动关联管理
- ✅ **异步任务队列** - 单线程任务处理，稳定可靠
- ✅ **错误日志** - 自动记录并保存详细错误信息

---

## 🚀 快速开始

### 环境要求

- Python 3.10+
- 有效的 LLM API Key（阿里云百炼 / DeepSeek 等）

### 安装依赖

```bash
cd ExDocIndex/src
pip install -r requirements.txt
```

### 配置 API

编辑 `src/settings.property` 文件：

```properties
# 工作目录（请使用绝对路径）
workdir = r"/path/to/ExDocIndex/WorkArea"

# LLM API 配置
llm_api_key = "sk-YOUR_API_KEY_HERE"
llm_base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
llm_model = "qwen3.5-plus"
```

### 启动 Web 管理系统

```bash
cd src/web
python run.py
```

访问 http://localhost:5000

---

## 📂 项目结构

```
ExDocIndex/
├── src/
│   ├── ChatClient.py         # OpenAI 兼容聊天客户端
│   ├── doc_summarizer.py     # 文档摘要生成器
│   ├── HTMLparse.py          # HTML 解析器
│   ├── PDFparse.py           # PDF 解析器（基于 MinerU）
│   ├── mcp_client.py         # MCP 客户端
│   ├── mcp_server.py         # MCP 服务端
│   ├── Utils.py              # 工具函数
│   ├── settings.property     # 配置文件 ⚠️ 请勿提交
│   ├── agents/               # AI Agent 提示词
│   │   ├── htmlparser.md     # HTML 解析提示词
│   │   ├── librarian.md      # 索引生成提示词
│   │   ├── mdparser.md       # Markdown 解析提示词
│   │   └── plaintext.md      # 纯文本解析提示词
│   ├── web/                  # Web 管理系统
│   │   ├── app.py            # Flask 应用
│   │   ├── database.py       # 数据库模型
│   │   ├── file_state.py     # 文件状态管理
│   │   ├── task_queue.py     # 异步任务队列
│   │   ├── templates/        # HTML 模板
│   │   └── static/           # 静态资源
│   └── cache/                # 临时缓存目录
├── WorkArea/                 # 工作目录
│   ├── InputDocs/            # 输入文档
│   └── Summary/              # 输出摘要
├── .gitignore                # Git 忽略配置
└── README.md                 # 项目说明
```

---

## 📖 使用文档

### 1. 上传文档

将需要处理的文档放入 `WorkArea/InputDocs/` 目录，或通过 Web 界面上传。

**支持的格式**：
- 📄 PDF（支持 OCR）
- 🌐 HTML
- 📝 Markdown
- 📄 TXT

### 2. 理解文档

对文档进行"理解"操作，生成结构化摘要：

```python
from doc_summarizer import understand_doc

understand_doc(
    doc_path="WorkArea/InputDocs/document.pdf",
    output_dir="WorkArea/Summary"
)
```

### 3. 构建索引

为理解后的文档创建索引：

```python
from doc_summarizer import summarize_doc

summarize_doc(
    doc_path="WorkArea/Summary/document.md",
    index_path="WorkArea/index.json"
)
```

### 4. 使用 MCP 服务

启动 MCP 服务器：

```bash
python src/mcp_server.py
```

MCP 提供的工具：
- `get_RealTime` - 获取当前时间
- `get_doc` - 读取文档内容
- `get_index` - 读取索引数据

---

## 🔧 API 配置

### 支持的 LLM 服务商

| 服务商 | Base URL | 推荐模型 |
|--------|----------|----------|
| 阿里云百炼 | `https://dashscope.aliyuncs.com/compatible-mode/v1` | qwen3.5-plus |
| DeepSeek | `https://api.deepseek.com` | deepseek-chat |
| OpenAI | `https://api.openai.com/v1` | gpt-4o |

### 获取 API Key

1. **阿里云百炼**: 访问 [dashscope.aliyun.com](https://dashscope.aliyun.com)
2. **DeepSeek**: 访问 [platform.deepseek.com](https://platform.deepseek.com)

---

## 🧪 测试

运行 Web 管理系统测试：

```bash
cd src/web
python test_system.py
```

---

## 📊 数据库结构

系统使用 SQLite 数据库 (`exdocindex.db`) 存储：

| 表名 | 描述 |
|------|------|
| `files` | 文件基本信息与状态 |
| `understanding_records` | 理解操作记录 |
| `index_records` | 索引数据记录 |
| `tasks` | 任务队列记录 |

---

## ⚠️ 安全提示

1. **保护 API Key**: `settings.property` 包含敏感信息，请勿提交到版本控制
2. **删除操作**: 删除文件会级联删除关联的理解结果和索引
3. **磁盘空间**: 大量文档会占用较多磁盘空间

---

## 🛠️ 故障排除

### 常见问题

**Q: 理解任务失败**
- 检查 API Key 是否有效
- 检查网络连接
- 查看 `src/web/error_logs/` 目录的错误日志

**Q: 索引质量为空**
- 确认文件是否已完成理解
- 检查文档内容是否适合索引

**Q: PDF 解析失败**
- 确保已安装 MinerU 依赖
- 检查 PDF 文件是否损坏

---

## 📄 许可证

MIT License

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

---

<div align="center">

**ExDocIndex** - 让文档检索更智能

Made with ❤️ by ExploitH

</div>
