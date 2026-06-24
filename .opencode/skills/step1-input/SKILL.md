---
name: step1-input
description: |
  Use when reading local requirement documents as the first step of test case generation.
  Trigger keywords: "读取需求", "导入需求", "加载需求", "输入需求".
  Supports: PDF (.pdf), Word (.docx), Markdown (.md), Images (.png/.jpg/.jpeg).
  Use ONLY after the user has specified a local file path to a requirement document.
---

# Step 1: 需求输入

从本地文件系统读取需求文档，提取原始文本内容。

## 重要：解析方式（必须遵守）

| 格式 | 解析方式 | 说明 |
|------|----------|------|
| PDF (.pdf) | **只能用** `scripts/extract.py` | 调用 pdfplumber 提取文本，**禁止用 Read tool** |
| Word (.docx) | **只能用** `scripts/extract.py` | 调用 python-docx 提取文本，**禁止用 Read tool** |
| Markdown (.md) | Read tool 直接读取 | 纯文本文件 |
| 图片 (.png/.jpg) | Read tool 多模态识别 | 需模型支持，否则走降级策略 |

> 当前模型（deepseek-v4-pro）不支持 PDF/图片的多模态输入。**PDF 和 Word 一律走 Python 脚本提取，绝不使用 Read tool。**

支持混合输入：PDF + 图片、多张图片、多个 Word 文件等组合场景。同时支持用户聊天中的文字描述作为补充需求。

## 前提：提供文件绝对路径

openencode 聊天上传的文件不会自动保存到磁盘。请用户提供需求文档的**本地绝对路径**（如 `D:\Documents\需求.pdf`），无需将文件复制到项目目录。工作目录和中间产物仍在 `.opencode/work/` 下，不影响源文件位置。

## 工作流程

1. **确认文件路径**：请用户提供需求文档的本地绝对路径
2. **校验文件**：检查文件是否存在、格式是否在支持列表中
3. **提取内容**：
   - PDF / Word：调用 Python 脚本 `scripts/extract.py` 解析
   - Markdown：直接使用 Read tool 读取
   - 图片：使用 Read tool 读取，获取多模态描述
4. **创建工作目录**：按 `文档名_日期` 格式创建专属目录（如 `登录需求_20250610`），路径为 `.opencode/work/<文档名_日期>/`
5. **保存中间产物**：将提取的原始文本保存到 `.opencode/work/<文档名_日期>/step1_raw_content.txt`
6. **记录当前工作目录**：将目录名写入 `.opencode/work/_current.txt`，供后续步骤读取

## 多图 / 混合格式场景

当需求由多张图片或多类型文件组成时：

1. **确认输入**：请用户提供文件路径列表或一个文件夹路径
2. **排序**：按文件名自然排序（如 `原型图_01.png`, `原型图_02.png`），保持逻辑顺序
3. **逐文件提取**：
   - 每张图片用 Read tool 单独识别，输出文字描述
   - PDF/Word/MD 按对应方式解析
4. **拼接**：所有文件内容按顺序拼接写入 `step1_raw_content.txt`，格式如下：
   ```
   === 文件: 原型图_01.png ===
   [图片多模态描述内容]
   
   === 文件: 原型图_02.png ===
   [图片多模态描述内容]
   
   === 文件: 需求补充.docx ===
   [Word 文档提取内容]
   ```
5. **命名规则**：
   - 如果输入包含文档文件（PDF/Word/MD），取第一个文档的文件名作为目录名
   - 如果全部是图片，请用户提供一个需求名称，或使用第一张图片的文件名
    - 无法自动确定名称时，主动询问用户

## 用户聊天描述 + 图片 场景

当用户在图之外还提供了口头/文字描述时：

1. 先将用户的文字描述作为独立一段写入文件头：
   ```
   === 用户补充描述 ===
   [用户在聊天中提供的需求说明文字]
   ```
2. 再将图片多模态描述拼接在后面
3. 用户描述可作为图片的标注和补充，Step2 会综合理解

## 文档内嵌图片场景

当 DOCX 或 PDF 文档内部嵌有截图、原型图时，纯文本提取会丢失图片信息。

### DOCX

`scripts/extract.py` 已内置内嵌图片提取功能：

1. 运行 `scripts/extract.py <file> --extract-images` 
2. 脚本提取文本，同时将内嵌图片保存到 `.opencode/work/<目录>/extracted_images/`
3. 对每张提取出的图片，使用 Read tool 做多模态识别
4. 将图片描述插入到文本中对应位置

### PDF

策略：如果 PDF 包含重要的内嵌图片，建议用户同时提供原始图片文件。如果必须从 PDF 提取，可安装 PyMuPDF：
```powershell
.venv\Scripts\pip.exe install PyMuPDF
```
然后用 `scripts/extract.py <file> --extract-images` 提取。

## 图片识别要点

用 GPT-4o（推荐）读取图片时，按以下结构化格式描述，使 Step2 能准确提取需求字段：

### 识别模板

对每张原型图/流程图，输出以下结构：

```
=== 图片: [文件名] ===

**界面/场景**: [这个画面的名称，如"登录页"、"匹配界面"]

**UI 元素清单**:
- 按钮: [名称, 位置, 状态]
- 输入框: [名称, 占位提示, 是否必填]
- 下拉/选择: [选项列表]
- 文本提示: [具体文案]

**当前显示状态**:
- [描述画面目前展示的状态，如"未开始, 显示'开始'按钮+红点"]

**可交互行为**:
- 点击XX按钮 → 预计跳转到XX
- 关闭弹窗 → 返回XX

**数据/规则线索**:
- [画面上出现的数值、范围、公式、逻辑条件]
- [表格中的字段名和数据]

**不明确的地方**: [画面中模糊或不确定的内容]
```

### 示例：入口状态截图

```
=== 图片: 入口-未开始.png ===

**界面/场景**: 主界面, 宝藏攀登入口

**UI 元素清单**:
- 按钮: 入口图标(右下角), 状态: 可点击
- 文本提示: 按钮上显示"开始"
- 红点: 按钮右上角, 表示有新活动

**当前显示状态**: 
- 入口已解锁但活动未开始, 显示"开始"文字+红点提示

**可交互行为**:
- 点击入口 → 预计弹出活动开启弹窗

**数据/规则线索**:
- 无

**不明确的地方**: 红点是否在点击后消失, 文档未说明
```

> 这种描述格式能让 Step2 的 LLM 直接提取 `expected_outputs`、`business_rules`、`preconditions` 等字段，减少解析偏差。

## 模型不支持图片时

当 Read tool 读取图片返回 `"this model does not support image input"` 时，不报错中断，而是给用户两个选择：

### 选项 A：切换多模态模型（推荐）

```
提示用户：
当前模型不支持图片识别。建议切换模型后继续：

  GPT-4o       / 推荐，性价比高
  GPT-4.5      / 更高精度
  Claude 3.5+  / 优秀的多模态理解
  Gemini 2.0 Flash / 有免费额度

切换方式：退出 opencode，用新模型重新打开，再次说"读取需求"。
```

用户切换模型后继续 Step1（图片识别走上方结构化模板），然后**用新模型直接接着跑 Step2~6，不需要再切回**——多模态模型处理文本任务完全没问题，多一次切换多一次浪费。

### 选项 B：跳过图片，纯文本继续

```
提示用户：
跳过图片处理，只用已有文本内容继续。
后续 Step2~6 不会包含图片中的需求信息，可能导致遗漏。
```

用户确认后，跳过图片，将已有的 PDF/Word/Markdown 文本写入 `step1_raw_content.txt`。

### 模型本身支持图片时

直接走上方「图片识别要点」的结构化模板，不提醒、不打断。

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

### DOCX 表格提取限制（重要）

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

### 提取后完整性校验

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
