# ExDocIndex Web 管理系统

这是一个智能文档索引生成与管理平台的 Web 界面。

## 🚀 功能特性

### 核心功能
- 📁 **文件管理**：支持上传、删除 PDF、HTML、MD、TXT 文件
- 🌳 **树形结构**：支持文件夹嵌套，树形组织文件
- 🤖 **智能理解**：使用 AI 模型自动解析文档，生成结构化 Markdown
- 📊 **索引构建**：为文档生成高质量索引，支持直接索引和二次索引
- 🔗 **强关联性**：源文件与理解文件强关联，删除源文件自动级联删除
- ⚙️ **异步任务队列**：单线程任务处理，防止内存溢出
- 📝 **错误日志**：自动保存错误日志到文件，方便调试

### 技术特性
- 💾 **SQLite 数据库**：完整的文件状态追踪系统
- 🔄 **实时状态更新**：5 秒自动刷新，实时显示任务状态
- 🎨 **现代化 UI**：响应式设计，支持移动端
- 🔔 **Toast 提示**：友好的用户反馈
- ⚠️ **确认对话框**：重要操作二次确认

## 📦 安装依赖

```bash
cd /home/exploith/ExDocIndex/src/web
pip install -r requirements.txt
```

## 🎯 快速开始

### 1. 启动服务器

```bash
python run.py
```

服务器将在 `http://localhost:5000` 启动。

### 2. 访问系统

打开浏览器访问：`http://localhost:5000`

### 3. 配置 API（可选）

进入"设置"页面，配置 LLM API 参数：
- API Key
- Base URL
- 模型名称

或者编辑 `/home/exploith/ExDocIndex/src/settings.property` 文件。

## 📖 使用指南

### 上传文件

1. 点击"上传文件"按钮
2. 选择要上传的文件（支持多选）
3. 文件将上传到当前目录

**支持格式**：PDF, HTML, Markdown, TXT  
**文件大小**：最大 100MB

### 新建文件夹

1. 点击"新建文件夹"按钮
2. 输入文件夹名称
3. 文件夹将在当前目录创建

### 理解文件

对文件进行"理解"操作：

1. 找到目标文件
2. 点击"理解"按钮
3. 任务将加入队列，状态显示为"运行中"
4. 完成后状态变为"已理解"

**注意**：
- PDF 文件：使用 MinerU 解析 + OCR 纠错
- HTML 文件：语义转换为 Markdown
- MD/TXT 文件：OCR 纠错和结构重组

### 查看理解结果

1. 文件状态为"已理解"后
2. 点击"查看"按钮
3. 在新窗口中查看理解后的 Markdown 内容

### 构建索引

为文件创建索引：

1. 找到目标文件
2. 点击"索引"按钮
3. 如果文件未理解，会弹出警告确认
4. 任务完成后，点击"索引"按钮查看索引数据

**索引模式**：
- **二次索引**：基于理解后的文件（推荐）
- **直接索引**：直接对原始文件索引（需确认）

### 删除文件

1. 点击"删除"按钮
2. 确认删除操作
3. 文件及其关联的理解文件、索引记录将被级联删除

**警告**：删除操作不可恢复！

## 🗂️ 目录结构

```
WorkArea/
├── InputDocs/          # 上传的原始文件
│   ├── file1.pdf
│   └── folder1/
│       └── file2.html
├── Summary/            # 理解后的 Markdown 文件
│   ├── file1.md
│   └── file2.md
├── index.json          # 索引数据文件
└── exdocindex.db       # SQLite 数据库
```

## 🔧 配置文件

编辑 `/home/exploith/ExDocIndex/src/settings.property`：

```properties
# 工作目录（绝对路径）
workdir = r"/home/exploith/ExDocIndex/WorkArea"

# LLM API 配置
llm_api_key = "your-api-key"
llm_base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
llm_model = "qwen3.5-plus"
```

## 📊 数据库结构

### files 表
文件基本信息和状态

### understanding_records 表
理解操作记录

### index_records 表
索引数据记录

### tasks 表
任务队列记录

## 🐛 错误处理

### 查看错误日志

错误日志保存在 `/home/exploith/ExDocIndex/src/web/error_logs/` 目录。

日志文件名格式：`task_{任务 ID}_{时间戳}.log`

### 常见问题

**Q: 文件上传失败**
- 检查文件大小是否超过 100MB
- 检查文件格式是否支持
- 检查磁盘空间

**Q: 理解任务失败**
- 检查 API Key 是否有效
- 检查网络连接
- 查看错误日志

**Q: 索引质量为空**
- 确认文件是否已理解
- 检查索引文件格式

## 🧪 运行测试

```bash
python test_system.py
```

测试项目：
- 数据库操作
- 文件状态管理
- 文件上传/删除
- 级联删除

## 📝 API 文档

### 文件管理 API

- `GET /api/files` - 列出文件
- `POST /api/files/upload` - 上传文件
- `DELETE /api/files/<id>` - 删除文件

### 理解操作 API

- `POST /api/files/<id>/understand` - 开始理解
- `GET /api/files/<id>/summary` - 获取理解结果

### 索引操作 API

- `POST /api/files/<id>/index` - 创建索引
- `GET /api/files/<id>/index` - 获取索引数据

### 任务管理 API

- `GET /api/tasks/<id>` - 获取任务状态
- `GET /api/tasks/queue` - 获取队列状态

## 🔐 安全说明

- 单用户本地使用，无需认证
- API Key 保存在配置文件中，请注意保密
- 删除操作有二次确认，但仍需谨慎

## 📞 技术支持

如遇问题，请查看：
1. 错误日志
2. 数据库状态
3. 任务队列状态

## 📄 许可证

本项目为 ExDocIndex 项目的一部分。
