---
name: step2-parse
description: |
  Use after step1-input, when raw requirement text is available.
  Trigger keywords: "解析需求", "提取需求", "结构化需求", "需求分析".
  Uses LLM to parse free-form requirement documents into structured JSON.
  Reads from `.opencode/work/<文档名_日期>/step1_raw_content.txt`, writes to `.opencode/work/<文档名_日期>/step2_requirements.json`.
  The working directory name is read from `.opencode/work/_current.txt`.
---

# Step 2: 需求解析

使用 LLM 将原始需求文本解析为结构化 JSON 数据。

## 输入

从 `.opencode/work/_current.txt` 获取当前工作目录名，然后读取该目录下的 `.opencode/work/<目录名>/step1_raw_content.txt`。

## 输出

解析后的结构化需求写入 `.opencode/work/<目录名>/step2_requirements.json`。

该文件是后续所有步骤的**唯一数据源**，Step3~Step5 都从此文件读取，不再接触原始文档。

### 产物归档

每个需求文档有独立的工作目录，全链路产物集中存放：

```
.opencode/work/<文档名_日期>/
├── step1_raw_content.txt      # Step1 原始文本
├── step2_requirements.json    # Step2 结构化需求
├── step3_features.json        # Step3 功能点清单
├── step4_testcases.json       # Step4 测试用例
└── testcases.xlsx             # Step5 最终用例文件
```

如果 Step3~Step5 生成结果异常，可从对应步骤的输入产物回溯排查。

## 解析流程

1. 读取 `.opencode/work/_current.txt` 获取当前工作目录名
2. 读取 `.opencode/work/<目录名>/step1_raw_content.txt` 获取原始文本
3. 分析文本结构，识别标题层级、功能段落、表格数据等
4. 按下方 Schema 提取并填充字段
5. 将结果写入 `.opencode/work/<目录名>/step2_requirements.json`

## 输出 Schema

```json
{
  "$schema": "requirement-parsed-v1",
  "meta": {
    "source_file": "原始文件名",
    "parse_time": "解析时间戳",
    "total_requirements": 3
  },
  "requirements": [
    {
      "id": "REQ-001",
      "module": "所属模块名",
      "feature": "功能点名称",
      "description": "功能的详细描述",
      "preconditions": ["前置条件1", "前置条件2"],
      "business_rules": ["业务规则1", "业务规则2"],
      "inputs": [
        { "name": "参数名", "type": "string/number/boolean/object", "required": true, "description": "说明" }
      ],
      "expected_outputs": ["预期输出1", "预期输出2"],
      "constraints": ["约束条件1"],
      "dependencies": ["REQ-002"],
      "notes": "补充说明"
    }
  ]
}
```

## 提取规则

- **module**: 从一级/二级标题推断，如 "## 用户管理" → module 为 "用户管理"
- **feature**: 从标题或功能描述段落中提炼，一句话概括
- **preconditions**: 识别 "前置条件"、"前提"、"假设" 等关键词所在段落
- **business_rules**: 识别数字范围、状态流转、权限矩阵等规则描述
- **inputs**: 从功能描述或表格中提取的输入字段，含类型和是否必填
- **expected_outputs**: 识别 "预期结果"、"期望"、"应显示" 等描述
- **constraints**: 性能要求、安全要求、兼容性要求等
- **dependencies**: 识别文中 "依赖"、"关联"、引用其他需求的部分
- **notes**: 原文中需要额外标注但无法归类的信息。**需求描述模糊时填入 `[待确认] 具体疑问`**

## 需求模糊处理

遇到以下情况不要猜测，标记 `[待确认]`：

| 模糊类型 | 示例 | 标记方式 |
|----------|------|----------|
| 时间不明确 | "活动持续时间"到底是多久？什么时候开始？ | `[待确认] 活动开始时间未说明` |
| 范围不明确 | "控制在6%~10%"是整数还是浮点？ | `[待确认] 百分比取值精度未说明` |
| 时区问题 | 跨天判断用什么时区？服务器还是本地？ | `[待确认] 跨天判断时区未说明` |
| 交互不明确 | 点击后是弹窗还是跳转？ | `[待确认] 交互方式未明确` |
| 缺字段 | 表格/配置缺少关键字段 | `[待确认] XX字段名未定义` |
| **数据缺失** | step1 中出现 `[MISSING_DATA]` 标记 | `[待确认: 数据缺失] 表格"XX"内容未提取，需补充后重新解析` |

标记后 LLM 仍需继续解析，但标注表示"这是我猜的，需要确认"。

### 数据缺失段的处理规则

当 step1 中某段落标题存在但内容为空（或被 `[MISSING_DATA]` 标记）时：

1. **必须**创建一条 REQ，而非跳过该功能
2. 在 `description` 中写入 `[待确认: 数据缺失] 原始文档"第X节 XX"的表格/内容未提取`
3. 在 `business_rules` / `expected_outputs` 中基于段落标题做最小推测
4. **不要编造表格数据**填入 `inputs` 或 `business_rules`
5. 这些 REQ 会在 Step3/4 中生成有限的用例，QA 审核时会发现并补充

## 注意事项

- ID 从 REQ-001 开始自增编号
- 一个功能点 = 一条 requirement，即使原文中描述在同一段落
- 无法确定的字段留空数组或 null，不要编造
- 表格内容优先提取为 inputs 或 business_rules
- 保留原文关键措辞，不做过度的同义改写
- 需求模糊时标记 `[待确认]`，不要编造填补
- **多文件输入**：如果原始文本包含 `=== 文件: xxx ===` 分割标记，说明需求来自多个文件（如多张原型图），需综合分析所有段落后提取需求，不同文件可能描述同一功能的不同视角
- **禁止按表格边界切 REQ**：如果原文中有"A表定义类型+B表定义规则"，不要拆成两个 REQ（一个管类型、一个管规则）。规则是类型的属性，应合并在同一 REQ 下。标准是：两张表描述的是同一个对象的行为 → 合并
