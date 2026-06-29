---
name: step1-input
description: |
  Use when reading local requirement documents as the first step of test case generation.
  Trigger keywords: "读取需求", "导入需求", "加载需求", "输入需求".
  Supports: PDF (.pdf), Word (.docx), Markdown (.md).
  For images (.png/.jpg/.jpeg), load step1-image skill alongside this one.
  Use ONLY after the user has specified a local file path to a requirement document.
---

# Step 1: 需求输入

从本地文件系统读取需求文档，提取原始文本内容。

> **图片处理**：如果需求包含图片文件，请同时加载 `step1-image` skill。

## 恢复检查

Step1 是流程起点，恢复场景主要是**重复执行**或**中途断掉**：

- **工作目录已存在**：如果 `.opencode/work/<目录名>/` 已存在且包含 `step1_raw_content.txt`：
  - 如果文件非空 → 询问用户是否重新提取（可能源文件已更新）
  - 如果文件为空 → 直接重新执行 Step1
- **提取脚本失败**：检查 `.venv` 虚拟环境依赖是否安装：
  ```powershell
  .venv\Scripts\Activate.ps1
  pip install pdfplumber python-docx Pillow
  ```

**断点恢复**：Step1 中断后直接重新运行即可，会覆盖旧文件。

## 重要：解析方式（必须遵守）

| 格式 | 解析方式 | 说明 |
|------|----------|------|
| PDF (.pdf) | **只能用** `scripts/extract.py` | 调用 pdfplumber 提取文本，**禁止用 Read tool** |
| Word (.docx) | **只能用** `scripts/extract.py` | 调用 python-docx 提取文本，**禁止用 Read tool** |
| Markdown (.md) | Read tool 直接读取 | 纯文本文件 |
| 图片 (.png/.jpg) | 加载 `step1-image` skill | 多模态识别，见 step1-image |

支持混合输入：PDF + 图片、多张图片、多个 Word 文件等组合场景。同时支持用户聊天中的文字描述作为补充需求。

## 前提：提供文件绝对路径

opencode 聊天上传的文件不会自动保存到磁盘。请用户提供需求文档的**本地绝对路径**（如 `D:\Documents\需求.pdf`），无需将文件复制到项目目录。工作目录和中间产物仍在 `.opencode/work/` 下，不影响源文件位置。

## 工作流程

1. **确认文件路径**：请用户提供需求文档的本地绝对路径
2. **校验文件**：检查文件是否存在、格式是否在支持列表中
3. **提取内容**：
   - PDF / Word：调用 Python 脚本 `scripts/extract.py` 解析
   - Markdown：直接使用 Read tool 读取
   - 图片：加载 `step1-image` skill 处理
4. **创建工作目录**：按 `文档名_日期` 格式创建专属目录（如 `登录需求_20250610`），路径为 `.opencode/work/<文档名_日期>/`
5. **保存中间产物**：将提取的原始文本保存到 `.opencode/work/<文档名_日期>/step1_raw_content.txt`
6. **记录当前工作目录**：将目录名写入 `.opencode/work/_current.txt`，供后续步骤读取

## 多文件 / 混合格式场景

当需求由多个文件组成时：

1. **确认输入**：请用户提供文件路径列表或一个文件夹路径
2. **排序**：按文件名自然排序，保持逻辑顺序
3. **逐文件提取**：各文件按对应方式解析（PDF/Word 走脚本，MD 走 Read tool，图片走 step1-image）
4. **拼接**：所有文件内容按顺序拼接写入 `step1_raw_content.txt`，格式如下：
   ```
   === 文件: 需求文档.docx ===
   [文档提取内容]
   
   === 文件: 原型图_01.png ===
   [图片多模态描述内容]
   ```
5. **命名规则**：
   - 如果输入包含文档文件（PDF/Word/MD），取第一个文档的文件名作为目录名
   - 如果全部是图片，请用户提供一个需求名称，或使用第一张图片的文件名
   - 无法自动确定名称时，主动询问用户

## 用户聊天描述 + 文件 场景

当用户在文件之外还提供了口头/文字描述时：

1. 先将用户的文字描述作为独立一段写入文件头：
   ```
   === 用户补充描述 ===
   [用户在聊天中提供的需求说明文字]
   ```
2. 再将各文件内容拼接在后面
3. 用户描述可作为文件的标注和补充，Step2 会综合理解

## DOCX 表格提取限制（重要）

`extract.py` 对 DOCX 表格的处理方式是 `cell.text` 拼接为一行字符串，**不保留表格的行列结构**。可能导致：

- 多列表格变为连续纯文本，字段间关系丢失
- 空单元格丢失（合并为连续字符串时无法区分列边界）
- 表格列标题与数据行混在一起无法解析

**应对策略**（按优先级）：

| 策略 | 适用场景 | 操作 |
|------|---------|------|
| 二次提取表格 | 表格较多或关键数据在表中 | 用 python 直接读 DOCX 的 `document.xml`，正则提取 `<w:tr>/<w:tc>/<w:t>` 获得结构化的行列表数据 |
| 单独运行表格提取 | 需要保留行列对应关系 | `python -c "from docx import Document; doc = Document('file.docx'); ..."` 用 `doc.tables` 遍历输出 |
| 标记缺失 | 表格提取失败时 | 在 step1 中写入 `[数据缺失: 表格未提取] 表名` |

## 提取后完整性校验

保存 step1_raw_content.txt 后，**必须执行以下检查**：

1. 扫描文件中所有以数字编号开头的段落标题（如 `2.1 xxx`、`3.2 xxx`）
2. 对比每个标题后是否有内容（非空行）
3. 发现以下模式时在文件末尾追加 `[MISSING_DATA]` 标记：

```
标题行后只有下一级标题，无正文内容
标题行后紧接空行或文件尾
标题中包含"表"字但该段无数字数据
```

示例标记格式：
```
[MISSING_DATA] 2.1 积分值表 — 表数据未提取，仅保留标题行
[MISSING_DATA] 4.3 红点规则 — 触发条件表缺失
```

这些标记会被 Step2 检测并写入 `[待确认]`，避免数据丢失传递到下游。

## Python 虚拟环境

依赖安装在项目根目录的 `.venv/` 中：

```powershell
# 首次使用前执行
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install pdfplumber python-docx Pillow
```

## 解析脚本

调用 `scripts/extract.py <file_path>` 进行解析：

```powershell
.venv\Scripts\python.exe scripts/extract.py "<文件路径>"
```

脚本自动识别文件类型并输出提取的文本内容。

## 输出

原始文本**持久化**到 `.opencode/work/<文档名_日期>/step1_raw_content.txt`，供 Step2 读取。

同时输出文件元信息：文件名、格式、页数/字数，供复查时比对。

## 命名规则

- `<文档名>` 取自原始文件名（去扩展名），中文保留
- `<日期>` 取当前日期，格式 YYYYMMDD（如 20250610）
- 示例：需求文档 `登录模块需求.docx` → 工作目录 `登录模块需求_20250610`

## 目录结构

```
.opencode/work/
├── _current.txt                    # 记录当前正在处理的工作目录名
├── 登录模块需求_20250610/
│   └── step1_raw_content.txt
├── 支付功能_20250611/
│   └── step1_raw_content.txt
└── ...
```
