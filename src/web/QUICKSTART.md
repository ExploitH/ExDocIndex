# ExDocIndex Web 管理系统 - 快速启动指南

## 🚀 5 分钟快速上手

### 步骤 1：安装依赖（1 分钟）

```bash
cd /home/exploith/ExDocIndex/src/web
pip install -r requirements.txt
```

### 步骤 2：配置 API（1 分钟）

编辑配置文件：

```bash
nano ../settings.property
```

修改以下内容：

```properties
workdir = r"/home/exploith/ExDocIndex/WorkArea"
llm_api_key = "你的 API Key"
llm_base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
llm_model = "qwen3.5-plus"
```

### 步骤 3：启动服务器（30 秒）

```bash
python run.py
```

看到以下输出表示启动成功：

```
============================================================
ExDocIndex Web 管理系统
============================================================

✓ 系统初始化完成

访问地址：http://localhost:5000

按 Ctrl+C 停止服务器

============================================================
 * Serving Flask app 'app'
 * Debug mode: on
 * Running on all addresses (0.0.0.0)
 * Running on http://127.0.0.1:5000
 * Running on http://xxx.xxx.xxx.xxx:5000
```

### 步骤 4：访问系统（30 秒）

打开浏览器，访问：`http://localhost:5000`

### 步骤 5：上传第一个文件（1 分钟）

1. 点击"文件管理"菜单
2. 点击"上传文件"按钮
3. 选择一个 PDF/HTML/MD/TXT 文件
4. 点击"上传"

### 步骤 6：体验智能理解（2 分钟）

1. 找到刚上传的文件
2. 点击"理解"按钮
3. 等待任务完成（状态从"运行中"变为"已理解"）
4. 点击"查看"按钮查看理解结果

### 步骤 7：构建索引（1 分钟）

1. 点击"索引"按钮
2. 确认操作
3. 等待任务完成
4. 点击"索引"按钮查看索引数据

---

## 📋 完整功能清单

### ✅ 文件管理
- [x] 上传文件（支持多选）
- [x] 新建文件夹
- [x] 删除文件（级联删除）
- [x] 树形目录浏览
- [x] 面包屑导航

### ✅ 智能理解
- [x] PDF 解析（MinerU + OCR 纠错）
- [x] HTML 转换（语义化 Markdown）
- [x] MD/TXT 重构（结构优化）
- [x] 异步任务队列
- [x] 实时状态显示

### ✅ 索引构建
- [x] 二次索引（基于理解文件）
- [x] 直接索引（基于原文件）
- [x] JSONL 格式输出
- [x] 索引查看

### ✅ 系统功能
- [x] API 配置管理
- [x] 错误日志保存
- [x] 任务状态追踪
- [x] 统计信息展示

---

## 🎯 常用操作速查

### 上传文件
```
文件管理 → 上传文件 → 选择文件 → 上传
```

### 新建文件夹
```
文件管理 → 新建文件夹 → 输入名称 → 创建
```

### 理解文件
```
文件列表 → 找到文件 → 点击"理解" → 等待完成
```

### 查看理解结果
```
文件列表 → 点击"查看" → 浏览 Markdown
```

### 构建索引
```
文件列表 → 点击"索引" → 确认 → 等待完成
```

### 删除文件
```
文件列表 → 点击"删除" → 确认删除
```

---

## 🔧 故障排查

### 问题 1：无法访问 http://localhost:5000

**解决方案**：
1. 检查服务器是否启动
2. 检查端口是否被占用
3. 尝试访问 `http://127.0.0.1:5000`

### 问题 2：上传文件失败

**解决方案**：
1. 检查文件大小（最大 100MB）
2. 检查文件格式（PDF/HTML/MD/TXT）
3. 检查磁盘空间

### 问题 3：理解任务失败

**解决方案**：
1. 检查 API Key 是否有效
2. 检查网络连接
3. 查看错误日志：`error_logs/` 目录

### 问题 4：索引质量为空

**解决方案**：
1. 确认文件是否已理解
2. 检查文件内容是否为空
3. 重新尝试索引

---

## 📞 获取帮助

### 查看日志
```bash
# 查看错误日志
ls -lh error_logs/
cat error_logs/task_*.log
```

### 查看数据库
```bash
# 使用 SQLite 命令行
sqlite3 WorkArea/exdocindex.db

# 查看所有文件
SELECT * FROM files;

# 查看任务队列
SELECT * FROM tasks;
```

### 系统测试
```bash
# 运行测试脚本
python test_system.py
```

---

## 🎓 进阶使用

### 批量上传文件
```bash
# 使用 curl 命令
for file in *.pdf; do
  curl -X POST -F "file=@$file" http://localhost:5000/api/files/upload
done
```

### 查看 API 状态
```bash
# 查看统计信息
curl http://localhost:5000/api/statistics

# 查看队列状态
curl http://localhost:5000/api/tasks/queue
```

### 备份数据库
```bash
# 备份数据库
cp WorkArea/exdocindex.db WorkArea/exdocindex.db.backup

# 备份索引
cp WorkArea/index.json WorkArea/index.json.backup
```

---

## 📚 完整文档

- **使用文档**：`README.md`
- **项目总结**：`PROJECT_SUMMARY.md`
- **API 文档**：查看 `app.py` 中的路由定义

---

**祝您使用愉快！** 🎉

如有问题，请查看错误日志或联系开发团队。
