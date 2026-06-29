# req2testcase · AI 测试用例生成器

基于 [opencode](https://opencode.ai) Skill 构建的 AI 工作流，把**需求文档**自动转化为**可交付的测试用例**。支持 PDF / Word / Markdown / 图片输入，全程人工确认节点把关，最终产出专业排版的多 Sheet Excel 用例。

## 特性

- 📄 **多格式输入**：PDF、Word（含内嵌图片）、Markdown、图片
- 🧠 **LLM 需求解析**：自由文本需求 → 结构化 JSON
- 🌲 **功能点分解**：拆解为原子可测功能点，生成 XMind 脑图供人工审核
- ✅ **用例生成 + 自动审查**：13 项自动质检（覆盖度、格式、边界值、枚举遍历、P0 分配等）
- 📊 **专业输出**：智能分 Sheet、条件着色、下拉选项、汇总统计
- 🔄 **增量维护**：需求变更时自动备份并合并，保留已审核内容
- 🛠️ **断点恢复**：支持工作中断后从断点续跑，不重头开始

## 工作流

```
Step1 需求输入   读取本地文档 (PDF/Word/MD/图片)
   │
Step2 需求解析   LLM 提取结构化需求
   │
Step3 功能点分解 拆解原子功能点 + XMind 脑图   【用户确认】
   │
Step4 用例生成   生成测试用例 + Excel 预览      【用户确认】
   │
Step5 用例审查   自动质检，输出审查报告        【用户确认】
   │
Step6 用例输出   智能分 Sheet + 专业排版，交付最终文件
```

> 交付后若需修改，独立触发 **Step7 维护**（增量更新 / 补充 / 废弃用例），不走上述主流程。

### 确认节点

| 步骤 | 确认内容 | 产物 |
|------|----------|------|
| Step3 | 功能点分解是否完整准确 | `step3_features.xmind` |
| Step4 | 用例是否覆盖全面 | `step4_testcases.xlsx` |
| Step5 | 审查报告，决定修改或通过 | `step5_review_report.md` |

## 环境要求

- [opencode](https://opencode.ai) CLI
- Python 3.9+
- 依赖：

```bash
pip install pdfplumber PyMuPDF python-docx openpyxl
```

| 依赖 | 用途 |
|------|------|
| `pdfplumber` | PDF 文本提取 |
| `PyMuPDF` (`fitz`) | PDF 内嵌图片提取 |
| `python-docx` | Word 文本 / 图片提取 |
| `openpyxl` | Excel 用例生成与排版 |

## 使用方式

在 opencode 会话中提供需求文档路径，按自然语言触发各步骤即可：

```
读取需求 D:\docs\登录模块需求.pdf
解析需求
分解功能点          # 确认 XMind 后继续
生成用例            # 确认 Excel 后继续
审查用例
输出用例
```

需求变更时：

```
修改用例 / 需求变更 / 补充用例
```

**错误恢复**（工作中断后）：

```powershell
# 检查当前状态
.venv\Scripts\python.exe scripts\validate.py check .opencode/work/<目录名>

# 查看从哪步恢复
.venv\Scripts\python.exe scripts\validate.py resume .opencode/work/<目录名>

# 清理损坏产物
.venv\Scripts\python.exe scripts\validate.py clean .opencode/work/<目录名>
```

## 项目结构

```
.
├── opencode.json              # opencode 配置（注册 skills 路径）
├── .opencode/
│   ├── skills/                # 工作流 Skill 定义
│   │   ├── testcase-gen/      # 主流程编排（Step1→6）
│   │   ├── step1-input/       # 需求输入（PDF/Word/MD）
│   │   ├── step1-image/       # 图片识别（独立 skill）
│   │   ├── step2-parse/       # 需求解析
│   │   ├── step3-breakdown/   # 功能点分解
│   │   ├── step4-generate/    # 用例生成
│   │   │   └── refs/          # 生成规则参考（rules.md、checklist.md）
│   │   ├── step5-review/      # 用例审查
│   │   ├── step6-output/      # 用例输出
│   │   └── step7-maintain/    # 售后维护（增量更新）
│   └── work/                  # 运行产物（已 gitignore）
└── scripts/                   # Python 工具脚本
    ├── extract.py             # 文档解析（PDF/Word + 图片）
    ├── generate_xmind.py      # 功能点 → XMind 脑图
    ├── generate_excel.py      # 用例 → Excel 预览
    ├── generate_final_excel.py# 最终多 Sheet 专业排版 Excel
    ├── review.py              # 用例自动审查（13 项检查）
    ├── validate.py            # 工作流校验与断点恢复
    ├── backup.py              # 变更前自动备份
    └── merge_testcases.py     # 增量合并用例
```

每个需求文档拥有独立工作目录，全链路产物集中存放、互不干扰：

```
.opencode/work/<文档名_日期>/
├── step1_raw_content.txt      # 原始文本
├── step2_requirements.json    # 结构化需求
├── step3_features.json/.xmind # 功能点
├── step4_testcases.json/.xlsx # 用例
├── step5_review_report.md     # 审查报告
└── backups/                   # 增量变更备份
```

## License

MIT
