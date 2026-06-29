---
name: step4-generate
description: |
  Use after step3-breakdown, once user has reviewed and confirmed the XMind feature points.
  Trigger keywords: "生成用例", "编写测试用例", "用例生成", "生成测试用例".
  Reads step3_features.json, generates detailed test cases, outputs JSON + Excel preview.
  User MUST review the Excel before proceeding to step5-output for final formatting.
---

# Step 4: 用例生成

根据确认后的功能点，逐条生成详细测试用例，产出 JSON 和 Excel 预览供用户审核。

## 恢复检查

执行本步骤前，先检查上游产物：

```powershell
.venv\Scripts\python.exe scripts\validate.py check .opencode/work/<目录名> --step 3
```

- 如果 Step1~3 产物正常 → 继续执行 Step4
- 如果 Step3 产物缺失 → 重新执行 Step3（`step3-breakdown`）
- 如果 `step3_features.json` JSON 解析失败 → 重新执行 Step3
- 如果 `step3_features.json` 中 `features` 为空数组 → 检查 Step2 的 `requirements` 是否为空

**断点恢复**：
- 如果 Step4 执行到一半中断 → 直接重新运行 Step4，会覆盖旧文件
- 如果已生成 JSON 但 Excel 生成失败 → 可单独调用 `scripts/generate_excel.py` 补生成

> **配套参考**：生成规则和自检清单已拆出至 `refs/` 目录：
> - `refs/rules.md`：边界值分析、枚举遍历、预期拆行、组件生命周期、跨表交叉验证
> - `refs/checklist.md`：生成前自检清单

## 输入

从 `.opencode/work/<工作目录>/step3_features.json` 读取已确认的功能点。

## 输出

| 文件 | 用途 |
|------|------|
| `step4_testcases.json` | 机器可读的用例数据，供 Step5 使用 |
| `step4_testcases.xlsx` | Excel 预览，供用户打开审核 |

## 工作流程

1. 读取 `step3_features.json`，获取所有已确认的测试场景
2. **去重检查**：扫描所有测试场景，识别跨 REQ 的重复覆盖（详见 `refs/rules.md`）
3. 对每个测试场景生成用例：
   - **数值区间场景**：用边界值法拆解，每条 FP 至少 3~4 条用例
   - **状态分支场景**：每种状态至少 1 条用例，包含状态内关键操作
   - **操作类场景**（点击跳转、按钮行为）：不重复验证已有状态，只测操作本身的跳转行为
4. 将用例写入 `step4_testcases.json`
5. 调用 `scripts/generate_excel.py` 生成 `step4_testcases.xlsx`
6. **暂停，请用户打开 Excel 审核确认后，再继续 Step5**

## Excel 表头

| 列 | 字段 | 说明 |
|----|------|------|
| A | 用例编号 | TC-001, TC-002... 自增 |
| B | 模块 | 所属模块名 |
| C | 测试点 | 对应 REQ 的功能名（如"入口显示与解锁"），相同测试点合并居中 |
| D | 用例标题 | 简洁概括场景（如"入口不显示-关卡小于10"），不写"验证"前缀 |
| E | 前置条件 | 执行用例前需满足的条件 |
| F | 测试步骤 | 编号步骤，如 "1.打开登录页\n2.输入账号密码\n3.点击登录" |
| G | 预期结果 | 期望看到的结果 |
| H | 优先级 | P0 / P1 / P2 / P3 |
| I | 测试结果 | 预留填写：P(Pass) / F(Fail) / N/A |
| J | 备注 | 其他补充说明 |

## 输出 Schema (JSON)

```json
{
  "$schema": "testcases-v1",
  "meta": {
    "source_file": "原始文件名",
    "total_features": 15,
    "total_testcases": 45
  },
  "testcases": [
    {
      "id": "TC-001",
      "feature_point": "入口显示与解锁",
      "feature_id": "FP-001",
      "module": "活动入口",
      "title": "入口不显示-关卡小于10",
      "preconditions": ["用户已注册", "账号状态正常"],
      "steps": ["打开登录页", "输入账号 test@test.com", "输入密码 Abc12345", "点击登录按钮"],
      "expected_results": ["页面跳转至首页", "标题栏显示用户昵称"],
      "priority": "P0",
      "test_result": "",
      "notes": ""
    }
  ]
}
```

### ⚠️ 字段类型契约（必须遵守，违反会导致渲染崩坏）

| 字段 | 类型 | 反例后果 |
|------|------|---------|
| `preconditions` | **JSON 数组**（字符串列表） | 写成字符串会被逐字符遍历，每个字带一个项目符号 |
| `steps` | **JSON 数组**（每步一个元素） | 写成字符串会被逐字符编号 |
| `expected_results` | **JSON 数组**（每个检查项一个元素） | 写成字符串会被逐字符编号；单数 `expected_result` 已弃用 |

- 即使只有一条，也要写成单元素数组：`"expected_results": ["xxx"]`。
- 统一用复数 `expected_results`，不要用单数 `expected_result`。

## 生成前自检

生成用例后，**必须逐项确认** `refs/checklist.md` 中的 8 项检查。
发现未通过时，补充用例直到清单全部通过，再生成 Excel。

## 生成规则

- 用例编号 TC-001 起自增，即使跨模块也不重置
- `feature_point` 填对应 REQ 的功能名（如"入口显示与解锁"），多个场景共用
- `title` 简洁概括本条用例的场景（如"入口不显示-关卡小于10"），不要写"验证""测试"等前缀
- 测试步骤必须编号，每条步骤一行，用换行符分隔
- 预期结果需明确可验证，避免"正常""成功"等模糊表述
- 涉及数值区间的用例，必须给出具体测试值，覆盖边界点
- **需求不明确时**：不要编造答案，在 `notes` 中写入 `[待确认] 具体疑问`，让 QA 评审时确认

## 需求不明确的处理

当生成用例时发现需求文档有歧义或遗漏：

1. 先在 `notes` 写入问题（如 `[待确认] 活动持续时间是自然天还是滚动24小时？`）
2. 按最常见的理解继续生成用例（不中断）
3. 生成完汇总所有 `[待确认]` 项，提醒用户检查

常见场景：
- 时间计算不明确（时区、起止点、精度）
- 数值范围不明确（取整方式、边界包不包含）
- 交互跳转不明确（弹窗/页面/刷新）
- 状态切换触发条件不明确

## 注意事项

- 用户审核确认前，不要启动 Step5
- Excel 中测试结果列默认为空
- 用 `openpyxl` 库生成 `.xlsx`，脚本路径：`scripts/generate_excel.py`
- **Excel 格式要求**：所有单元格统一使用左对齐 + 垂直居中（horizontal=left, vertical=center），表头可保持居中但正文数据区必须左对齐垂直居中
