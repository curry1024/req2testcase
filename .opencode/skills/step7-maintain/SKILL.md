---
name: step7-maintain
description: |
  Use ONLY when user wants to MODIFY EXISTING test cases after initial generation is complete.
  Trigger keywords: "修改用例", "更新需求", "需求变更", "增量更新", "补充用例", "删用例", "废弃".
  NOT part of the step1→6 workflow. Triggered independently when user has existing test cases and wants changes.
  After delivery: Step7 (售后) handles incremental changes, backups, and merges.
---

# Step 7: 售后服务

处理上线后的用例维护场景。根据变更粒度智能选择最少步骤，避免全量重跑。

## 三种变更场景

| 场景 | 触发方式 | 处理策略 | 耗时 |
|------|----------|----------|------|
| 用例微调 | 用户口头：「TC-003 的步骤不够详细」 | 直接编辑 JSON，重生成 Excel | 秒级 |
| 需求小变 | 用户口头：「密码长度改为8位」 | 增量重跑影响到的 Step2→4，合并到已有 JSON | 分钟级 |
| 需求大变 | 用户提供新文档 | 全量重跑 Step1→6，旧版本归档保留 | 完整流程 |

## 工作流程

### 通用前置：备份

每次修改前，自动备份当前工作目录到 `.opencode/work/<工作目录>/backups/`：

```
backups/
├── 20250610_1430/        # 备份时间戳
│   ├── step3_features.json
│   └── step4_testcases.json
└── 20250611_0900/
    └── ...
```

备份由 `scripts/backup.py` 执行。

### 路由判断（LLM 决策）

根据用户的变更描述，判断走哪条路径：

```
用户输入
  │
  ├── 只改某几条用例的措辞/步骤？        → 用例微调
  ├── 改某个功能点的行为/规则/输入？     → 需求小变
  ├── 新增整个模块/功能？               → 需求小变（增量追加）
  ├── 上传了新需求文档？                 → 需求大变
  └── 需求文档全量替换？                 → 需求大变
```

### 路径 1：用例微调

1. 备份当前 JSON
2. LLM 直接编辑 `step4_testcases.json` 中指定用例
3. 调用 `scripts/generate_final_excel.py` 重新生成最终 Excel
4. 完成，无需重跑任何 Step

### 路径 2：需求小变 / 增量追加

1. 备份当前 JSON
2. 用户描述变更内容，LLM 提取变更的 REQ 范围
3. 对受影响的 REQ：重跑 Step2 解析 → Step3 分解 → Step4 生成
4. 调用 `scripts/merge_testcases.py` 将新用例合并入现有 JSON：
   - 已有用例保持不变（ID、步骤、预期结果不覆盖）
   - 新增功能点的用例追加到末尾，编号递增
   - 已废弃功能点的用例自动标记
5. 重跑 Step5 审查 + Step6 生成最终 Excel

### 路径 3：需求大变 / 新文档

1. 备份当前工作目录
2. 用户可选择：
   - a. 创建新的工作目录（如 `需求_v2_20250611`），旧目录保留查询
   - b. 覆盖当前目录，先完整备份到 backups/
3. 全量重跑 Step1 → Step6

## 合并脚本

```powershell
.venv\Scripts\python.exe scripts\merge_testcases.py \
  --existing <现有 step4_testcases.json> \
  --new <新生成的 step4_testcases.json> \
  --output <合并后输出路径>
```

合并规则：
- 相同 `feature_id` 的用例：保留旧数据（已审核的），新增的追加
- 旧有但新 JSON 中不存在的用例：标记 `notes` 为 "[已废弃]"
- 新功能点的用例：追加到末尾，ID 从最大编号 +1 开始

## 备份脚本

```powershell
.venv\Scripts\python.exe scripts\backup.py <工作目录路径>
```

备份当前 `.json` 文件到 `backups/<时间戳>/`。

## 注意事项

- 不处理测试结果字段（P/F/N/A），用户自行在云文档中管理
- 备份保留最近 10 个时间点，超过则清理最旧的
- 用户可以直接要求回滚到某个备份版本
