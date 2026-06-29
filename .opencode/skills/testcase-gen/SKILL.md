---
name: testcase-gen
description: |
  Use when the user wants to generate test cases from requirement documents for the FIRST TIME.
  Trigger keywords: "生成测试用例", "测试用例", "需求分析", "用例生成".
  This skill covers the initial generation workflow: Step1→Step6.
  For modifications to existing test cases, use step7-maintain (triggered independently by "修改用例", "需求变更" etc).
  Step1 (输入) -> Step2 (解析) -> Step3 (分解) -> Step4 (生成) -> Step5 (审查) -> Step6 (输出).
---

# 测试用例生成器

从需求文档自动生成测试用例的完整工作流。

## 工作流

```
Step1: 需求输入     -- 读取本地文档 (PDF/Word/MD)
  │                    如果包含图片，同时加载 step1-image
Step2: 需求解析     -- LLM 提取结构化需求信息
    |
Step3: 功能点分解   -- 拆解为原子可测功能点 + 生成 XMind 脑图
    |                   【用户确认后继续】
Step4: 用例生成     -- 为每个功能点生成测试用例 + 生成 Excel 预览
    |                   【用户确认后继续】
Step5: 用例审查     -- 自动化质检，发现覆盖缺失/格式问题/模糊表述
    |                   【用户确认后继续】
Step6: 用例输出     -- 智能分Sheet + 专业排版，交付最终文件
```

> 用例交付后有修改需求，用户会独立触发 `step7-maintain`，不走此工作流。

## 确认节点

| 步骤 | 确认内容 | 产物 |
|------|----------|------|
| Step3 | 用户审核 XMind 功能点分解是否完整准确 | step3_features.xmind |
| Step4 | 用户审核 Excel 用例是否覆盖全面 | step4_testcases.xlsx |
| Step5 | 用户查看审查报告，决定修改或通过 | step5_review_report.md |

## 使用方式

用户提供需求文档路径后，按顺序调用各步骤 skill：

1. **step1-input**: 读取并提取文档原始内容
   - 如果需求包含图片（.png/.jpg/.jpeg），同时加载 **step1-image**
2. **step2-parse**: LLM 解析需求为结构化 JSON
3. **step3-breakdown**: 拆解功能点 + 生成 XMind，用户确认
4. **step4-generate**: 生成用例 + Excel 预览，用户确认
   - 生成规则详见 `step4-generate/refs/rules.md`
   - 自检清单详见 `step4-generate/refs/checklist.md`
5. **step5-review**: 自动审查用例质量，用户确认
6. **step6-output**: 最终格式化输出

## 产物归档

每个需求文档有独立工作目录，全链路产物集中存放，互不干扰：

```
.opencode/work/
├── _current.txt                       # 当前正在处理的工作目录名
├── 登录模块需求_20250610/
│   ├── step1_raw_content.txt          # Step1 原始文本
│   ├── step2_requirements.json        # Step2 结构化需求
│   ├── step3_features.json            # Step3 功能点 JSON
│   ├── step3_features.xmind           # Step3 功能点脑图（确认用）
│   ├── step4_testcases.json           # Step4 用例 JSON
│   ├── step4_testcases.xlsx           # Step4 用例 Excel（确认用）
│   ├── step5_review_report.md         # Step5 审查报告
│   ├── step5_review_result.json       # Step5 审查结果
│   └── backups/                       # Step7 自动备份
│       ├── 20250610_1430/
│       └── 20250611_0900/
└── 支付功能_20250611/
    └── ...
```

出问题时，从对应文档的目录向上溯源排查。

## 错误恢复与断点续跑

当某一步骤执行失败或中途断掉时，使用 `scripts/validate.py` 检查产物状态并确定恢复点：

### 检查当前状态

```powershell
# 检查所有步骤产物
.venv\Scripts\python.exe scripts\validate.py check .opencode/work/<目录名>

# 输出应从哪一步恢复
.venv\Scripts\python.exe scripts\validate.py resume .opencode/work/<目录名>
```

### 清理损坏产物

```powershell
# 清理损坏的产物，保留最后一步有效的
.venv\Scripts\python.exe scripts\validate.py clean .opencode/work/<目录名>
```

### 恢复策略

| 失败场景 | 恢复方式 |
|----------|----------|
| 某步执行到一半中断 | 直接重新运行该步骤，会覆盖旧文件 |
| 上游产物缺失/损坏 | 用 `validate.py resume` 找到断点，从该步重新执行 |
| JSON 解析失败 | 检查文件是否截断，重新运行上一步 |
| 模型超时/上下文溢出 | 重新运行该步骤，或拆分需求后分批处理 |
| 脚本执行失败 | 检查 Python 依赖（`.venv`）和脚本路径 |

### 各步骤恢复指引

每个步骤的 SKILL.md 开头都有「恢复检查」段落，说明该步骤的前置检查和断点恢复方式。

