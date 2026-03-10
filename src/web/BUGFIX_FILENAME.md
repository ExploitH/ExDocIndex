# Bug 修复：文件名保存错误

## 🐛 问题描述

上传文件后，文件列表中显示的不是完整文件名，而是只显示扩展名。例如：
- 上传 `abc.pdf` 显示为 `pdf`
- 上传 `文件.html` 显示为 `html`

此外，上传同名文件时会出现错误提示。

## 🔍 根本原因

问题出在 `app.py` 中使用了 `werkzeug.utils.secure_filename` 函数处理文件名。

该函数会将中文字符转换为空字符串，例如：
```python
from werkzeug.utils import secure_filename

secure_filename('abc.pdf')      # 返回 'abc.pdf' ✓
secure_filename('文件.html')     # 返回 'html' ✗ (中文被删除)
secure_filename('测试文件.md')   # 返回 'md' ✗ (中文被删除)
```

这是因为 `secure_filename` 设计用于处理英文文件名，会移除所有非 ASCII 字符。

## ✅ 解决方案

实现了一个新的 `sanitize_filename` 函数，保留中文字符：

```python
def sanitize_filename(filename: str) -> str:
    """清理文件名，保留中文字符，只移除危险字符"""
    # 保留中文、英文、数字、常见符号，移除路径分隔符等危险字符
    safe_name = re.sub(r'[^\w\u4e00-\u9fff\.\-\s]', '_', filename)
    # 替换多个连续下划线为单个
    safe_name = re.sub(r'_+', '_', safe_name)
    # 移除开头和结尾的下划线、空格
    safe_name = safe_name.strip('_ ').strip('.')
    return safe_name if safe_name else 'unnamed_file'
```

### 测试对比

| 原始文件名 | secure_filename | sanitize_filename |
|-----------|----------------|-------------------|
| `abc.pdf` | `abc.pdf` ✓ | `abc.pdf` ✓ |
| `123.pdf` | `123.pdf` ✓ | `123.pdf` ✓ |
| `文件.html` | `html` ✗ | `文件.html` ✓ |
| `测试文件.md` | `md` ✗ | `测试文件.md` ✓ |
| `test file.txt` | `test_file.txt` | `test file.txt` |
| `特殊@#字符.doc` | `_.doc` | `特殊_字符.doc` |
| `中文 English 混合.pdf` | `English.pdf` | `中文 English 混合.pdf` ✓ |

## 📝 修改内容

### 1. 添加 `sanitize_filename` 函数

**文件**: `app.py`

在文件顶部添加函数定义（第 157 行之后）：

```python
def sanitize_filename(filename: str) -> str:
    """
    清理文件名，保留中文字符，只移除危险字符
    """
    # 保留中文、英文、数字、常见符号，移除路径分隔符等危险字符
    # 只保留文件名基本字符：字母、数字、中文、下划线、点、空格
    safe_name = re.sub(r'[^\w\u4e00-\u9fff\.\-\s]', '_', filename)
    # 替换多个连续下划线为单个
    safe_name = re.sub(r'_+', '_', safe_name)
    # 移除开头和结尾的下划线、空格
    safe_name = safe_name.strip('_ ').strip('.')
    return safe_name if safe_name else 'unnamed_file'
```

### 2. 修改上传文件处理

**文件**: `app.py` - `upload_file()` 函数

**修改前**：
```python
filename = secure_filename(file.filename)
```

**修改后**：
```python
# 清理文件名（保留中文）
original_filename = file.filename
filename = sanitize_filename(original_filename)

# 确保有扩展名
if '.' not in filename and '.' in original_filename:
    ext = original_filename.split('.')[-1]
    filename = f'{filename}.{ext}'
```

### 3. 修改覆盖上传处理

**文件**: `app.py` - `overwrite_file()` 函数

**修改前**：
```python
filename = secure_filename(file.filename)
```

**修改后**：
```python
original_filename = file.filename
filename = sanitize_filename(original_filename)

# 确保有扩展名
if '.' not in filename and '.' in original_filename:
    ext = original_filename.split('.')[-1]
    filename = f'{filename}.{ext}'
```

### 4. 更新导入

**文件**: `app.py`

**修改前**：
```python
from werkzeug.utils import secure_filename
```

**修改后**：
```python
import re
```

## 🧪 测试结果

运行测试脚本 `test_filename_fix.py`：

```
============================================================
测试文件名上传修复
============================================================

上传文件测试：
  ✓ abc.pdf                        -> ID=1, 路径=InputDocs/abc.pdf
    数据库验证：abc.pdf ✓
  ✓ 123.pdf                        -> ID=2, 路径=InputDocs/123.pdf
    数据库验证：123.pdf ✓
  ✓ 测试文件.html                      -> ID=3, 路径=InputDocs/测试文件.html
    数据库验证：测试文件.html ✓
  ✓ 测试文件.md                        -> ID=4, 路径=InputDocs/测试文件.md
    数据库验证：测试文件.md ✓
  ✓ 中文 English 混合.txt              -> ID=5, 路径=InputDocs/中文 English 混合.txt
    数据库验证：中文 English 混合.txt ✓

文件列表：
  - 123.pdf (类型：pdf)
  - abc.pdf (类型：pdf)
  - 中文 English 混合.txt (类型：txt)
  - 测试文件.html (类型：html)
  - 测试文件.md (类型：md)

冲突检测测试：
  ✓ 正确检测到冲突：文件已存在：abc.pdf

✓ 测试环境已清理

============================================================
所有测试通过！
============================================================
```

## ✅ 验证步骤

1. **重启服务器**
   ```bash
   # 停止当前运行的服务器（Ctrl+C）
   python run.py
   ```

2. **上传测试文件**
   - 上传 `abc.pdf`
   - 上传 `123.pdf`
   - 上传 `测试文件.html`
   - 上传 `中文 English 混合.txt`

3. **验证显示**
   - 文件列表应显示完整文件名
   - 不应只显示扩展名

4. **验证冲突检测**
   - 再次上传 `abc.pdf`
   - 应提示"文件已存在，请重命名或选择覆盖"
   - 点击"覆盖"应成功，不再报错

## 📚 相关文件

- `app.py` - 主应用文件（已修复）
- `test_filename_fix.py` - 测试脚本
- `file_state.py` - 文件状态管理器（无需修改）
- `database.py` - 数据库模型（无需修改）

## 🔒 安全性说明

新的 `sanitize_filename` 函数仍然保持了安全性：

1. **移除路径分隔符**：防止目录遍历攻击
2. **移除特殊字符**：只保留安全字符（字母、数字、中文、下划线、点、连字符、空格）
3. **替换危险字符**：将不安全字符替换为下划线
4. **清理首尾**：移除开头和结尾的特殊字符

## 📅 修复日期

2026-03-10

## 👤 修复者

ExDocIndex Development Team

---

**Bug 已修复，测试通过！** ✅
