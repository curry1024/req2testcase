---
name: step6-output
description: |
  Use after step5-review, when all issues are resolved and user confirms final output.
  Trigger keywords: "输出用例", "导出用例", "最终用例", "生成最终文件".
  LLM analyzes test cases and decides intelligent sheet splitting strategy.
  Generates professionally formatted multi-sheet Excel file.
---

# Step 6: 最终输出

智能分析用例内容，生成可直接交付 QA 团队的专业 Excel 文件。

## 输入

从 `.opencode/work/<工作目录>/step4_testcases.json` 读取最终确认的用例。

## 输出

生成到**项目根目录**：

```
<文档名>_测试用例_v1.xlsx
```

## 工作流程

1. 读取 `step4_testcases.json` 获取最终用例
2. **LLM 分析分 Sheet 策略**（见下方规则）
3. 通知用户分 Sheet 方案，征得确认
4. 调用 `scripts/generate_final_excel.py` 生成最终文件
5. 输出文件路径

## 分 Sheet 策略（LLM 智能判断）

不要机械地按模块拆分。需要综合分析以下维度：

### 必须拆的情况

- 用例跨越明显不同的**场景域**（如 对局内 / 对局外、客户端 / 服务端、前台 / 后台）
- 用例涉及的**生命周期阶段**差异大（如 注册 / 使用 / 注销）
- 用户角色不同但都有关联（如 管理员操作 / 普通用户操作）

### 应该合的情况

- 两个模块高度耦合，分开反而不直观（如 商品浏览 + 购物车 + 下单 → 合为"交易流程"）
- 单个模块用例子项 < 5 条，不值得独立成 Sheet

### 参考拆分维度（优先级从高到低）

| 维度 | 示例 |
|------|------|
| 场景域 | 对局内、对局外、匹配中、结算时 |
| 业务流程 | 注册流程、交易流程、退款流程 |
| 系统边界 | 客户端行为、服务端逻辑、数据校验 |
| 模块 | 用户管理、商品管理、订单管理 |

### 最终输出 Sheet 结构示例

假设需求涉及登录和游戏战斗两个场景域：

```
Sheet「汇总」        -- 全局统计概览
Sheet「登录模块」    -- 登录、注册相关用例
Sheet「对局内」      -- 战斗、操作、结算用例
Sheet「对局外」      -- 大厅、匹配、社交用例
```

## Excel 排版规格

| 特性 | 规格 |
|------|------|
| 表头样式 | 绿底黑字(#548235)，微软雅黑 11pt 加粗 |
| 数据样式 | 微软雅黑 10pt |
| 模块/测试点合并 | **按值整组合并**：跨用例相同的模块/测试点合并为一格（基于源数据值判断，不读已合并单元格，避免被 None 误断） |
| 多行用例合并 | 一条用例含多条预期 → 展开为多行；**仅合并 编号/标题/前置/步骤**；**预期结果/优先级/测试结果/备注 逐行独立**（每条预期可单独判 P/F、单独提 BUG） |
| 优先级着色 | P0 浅红、P1 浅橙、P2 浅黄、P3 浅灰 |
| 测试结果 | 浅绿底，下拉选项 P / F / N/A（逐行各一格） |
| 冻结 | 首行 + 首列冻结 |
| 筛选 | 自动筛选 |
| 边框 | 浅灰细线 |

## 生成脚本

```powershell
.venv\Scripts\python.exe scripts/generate_final_excel.py "<json_path>" --output "<输出文件名>"
```

脚本接受 LLM 输出的 Sheet 分组方案，按方案生成多 Sheet 文件。

## 注意事项

- 文件名中的版本号从 v1 起，如果该文件已存在自动递增为 v2
- 测试结果列设置数据验证（下拉框：P, F, N/A）
- 汇总 Sheet 包含：用例总数、Sheet 分布、优先级分布
