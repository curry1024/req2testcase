"""
测试用例自动审查脚本
输入: step3_features.json (功能点), step4_testcases.json (用例)
输出: 审查结果 JSON + Markdown 报告

用法: python review.py <step3_json> <step4_json> [--output-dir <dir>]
"""
import json
import sys
import re
import os
from datetime import datetime


def load_json(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def count_steps(steps):
    """统计有效步骤数：单字符串按换行拆分，列表按元素累加（兼容新旧两种写法）。"""
    if not steps:
        return 0
    if isinstance(steps, str):
        steps = [steps]
    total = 0
    for s in steps:
        lines = [ln for ln in str(s).split("\n") if ln.strip()]
        total += len(lines)
    return total


def check_coverage(features, testcases):
    """检查功能点覆盖度"""
    issues = []
    feature_ids = {fp["id"]: fp for fp in features}
    covered = set()

    for tc in testcases:
        fid = tc.get("feature_id", "")
        if fid:
            covered.add(fid)

    for fid, fp in feature_ids.items():
        if fid not in covered:
            issues.append({
                "severity": "严重",
                "check": "覆盖缺失",
                "detail": f"{fid} ({fp.get('name', '')}) 无对应用例",
                "suggestion": f"建议至少补充 {fp.get('category', '')} 类用例",
            })

    return issues


def check_completeness(features, testcases):
    """检查用例字段完整性"""
    issues = []
    required_fields = ["id", "title", "steps"]

    for tc in testcases:
        for field in required_fields:
            value = tc.get(field)
            if not value:
                issues.append({
                    "severity": "严重",
                    "check": "字段缺失",
                    "detail": f"{tc.get('id', '未知')} 缺少 {field}",
                    "suggestion": f"请填写 {field} 字段",
                })

        # 预期结果：兼容 expected_results(复数列表) 或 expected_result(单数字符串)
        if not (tc.get("expected_results") or tc.get("expected_result")):
            issues.append({
                "severity": "严重",
                "check": "字段缺失",
                "detail": f"{tc.get('id', '未知')} 缺少 预期结果(expected_results)",
                "suggestion": "请填写 expected_results 字段",
            })

        # 步骤检查（按有效步骤数，兼容单字符串多步写法）
        steps = tc.get("steps", [])
        step_n = count_steps(steps)
        if steps and step_n < 2:
            issues.append({
                "severity": "轻微",
                "check": "步骤过于简略",
                "detail": f"{tc.get('id', '未知')} 仅有 {step_n} 个步骤",
                "suggestion": "建议将关键操作拆分为多个步骤",
            })

    return issues


def check_numbering(features, testcases):
    """检查编号连续性"""
    issues = []
    prev_num = 0

    for tc in testcases:
        tid = tc.get("id", "")
        match = re.match(r"TC-(\d+)", tid)
        if match:
            num = int(match.group(1))
            if prev_num > 0 and num != prev_num + 1:
                issues.append({
                    "severity": "轻微",
                    "check": "编号不连续",
                    "detail": f"{tid} 前一个编号为 TC-{prev_num:03d}，跳过了 {num - prev_num - 1} 个编号",
                    "suggestion": "检查是否漏掉了用例或编号重复",
                })
            prev_num = num

    return issues


def check_step_format(features, testcases):
    """检查步骤是否存在空白项（编号由导出脚本自动添加，不再强制步骤内联编号）"""
    issues = []

    for tc in testcases:
        steps = tc.get("steps", [])
        if isinstance(steps, str):
            steps = [steps]
        for i, step in enumerate(steps):
            if not str(step).strip():
                issues.append({
                    "severity": "轻微",
                    "check": "步骤格式",
                    "detail": f"{tc.get('id', '未知')} 步骤 {i+1} 为空",
                    "suggestion": "删除空步骤或补全步骤内容",
                })

    return issues


def check_priority_distribution(features, testcases):
    """检查优先级分布"""
    issues = []

    total = len(testcases)
    if total == 0:
        return issues

    counts = {"P0": 0, "P1": 0, "P2": 0, "P3": 0}
    for tc in testcases:
        p = tc.get("priority", "")
        if p in counts:
            counts[p] += 1

    p0_ratio = counts["P0"] / total * 100
    if p0_ratio > 50:
        issues.append({
            "severity": "提示",
            "check": "优先级分布",
            "detail": f"P0 用例占比 {p0_ratio:.0f}%，超过 50%",
            "suggestion": "P0 应为核心流程，检查是否过度标记",
        })

    if counts["P3"] == 0:
        issues.append({
            "severity": "提示",
            "check": "优先级分布",
            "detail": "无 P3 用例",
            "suggestion": "低优先级的边界/兼容性场景可标记为 P3",
        })

    return issues


def check_vague_expressions(features, testcases):
    """规则层面检查模糊表述"""
    issues = []
    vague_patterns = [
        (r"正常", "预期结果中包含模糊词\"正常\""),
        (r"成功$", "预期结果以\"成功\"结尾，建议具体描述"),
        (r"有效值", "测试数据中使用模糊词\"有效值\""),
        (r"任意", "测试数据中使用模糊词\"任意\""),
    ]

    for tc in testcases:
        expected = tc.get("expected_result", "")
        for pattern, msg in vague_patterns[:2]:  # 预期结果检查
            if re.search(pattern, str(expected)):
                issues.append({
                    "severity": "提示",
                    "check": "模糊表述",
                    "detail": f"{tc.get('id', '未知')}: {msg}",
                    "suggestion": "用具体的业务描述替代模糊词",
                })

        test_data = tc.get("test_data", "")
        for pattern, msg in vague_patterns[2:]:  # 测试数据检查
            if re.search(pattern, str(test_data)):
                issues.append({
                    "severity": "提示",
                    "check": "模糊表述",
                    "detail": f"{tc.get('id', '未知')}: {msg}",
                    "suggestion": "测试数据应给出具体可执行的值",
                })

    return issues


def check_expected_results(features, testcases):
    """检查同一用例的预期结果是否存在完全重复项"""
    issues = []

    for tc in testcases:
        expected = tc.get("expected_results")
        if expected is None:
            single = tc.get("expected_result")
            expected = [single] if single else []
        if not isinstance(expected, list):
            expected = [expected]

        seen = {}
        for item in expected:
            key = re.sub(r"\s+", "", str(item)).strip()
            if not key:
                continue
            seen[key] = seen.get(key, 0) + 1

        for key, cnt in seen.items():
            if cnt > 1:
                issues.append({
                    "severity": "轻微",
                    "check": "预期结果重复",
                    "detail": f"{tc.get('id', '未知')}: 预期结果中存在 {cnt} 处完全重复项「{key}」",
                    "suggestion": "删除重复项，或针对不同场景/渠道写出可区分的预期结果",
                })

    return issues


def check_schema_types(features, testcases):
    """检查 JSON Schema 类型契约：preconditions/steps/expected_results 必须是数组"""
    issues = []
    array_fields = {
        "preconditions": "前置条件",
        "steps": "测试步骤",
        "expected_results": "预期结果",
    }

    for tc in testcases:
        for field, label in array_fields.items():
            value = tc.get(field)
            if value is not None and not isinstance(value, list):
                issues.append({
                    "severity": "严重",
                    "check": "Schema 类型错误",
                    "detail": f"{tc.get('id', '未知')} 的 {field}({label}) 是 {type(value).__name__}，应为 JSON 数组",
                    "suggestion": f"将 {label} 改为数组格式，如 [\"{value}\"]",
                })

    return issues


def check_boundary_coverage(features, testcases):
    """检查 range 类型功能点的边界值覆盖（N-1, N, N+1）"""
    issues = []

    # 提取 range 类型 FP
    range_fps = {fp["id"]: fp for fp in features if fp.get("category") == "range"}

    if not range_fps:
        return issues

    # 从 FP description 中提取数值
    number_pattern = re.compile(r'(\d+(?:\.\d+)?)')

    for fp_id, fp in range_fps.items():
        desc = fp.get("description", "")
        numbers = [int(n) for n in number_pattern.findall(desc) if int(n) > 0]

        if not numbers:
            continue

        # 找到该 FP 对应的用例
        fp_testcases = [tc for tc in testcases if tc.get("feature_id") == fp_id]

        if not fp_testcases:
            issues.append({
                "severity": "严重",
                "check": "边界值缺失",
                "detail": f"{fp_id} ({fp.get('name', '')}) 为 range 类型但无任何用例",
                "suggestion": f"至少补充 3 条边界值用例（上边界-1, 上边界, 上边界+1）",
            })
            continue

        # 检查用例标题/步骤/预期中是否包含边界数值
        tc_text = " ".join([
            " ".join([
                t.get("title", ""),
                " ".join(t.get("steps", [])),
                " ".join(t.get("expected_results", [])),
            ])
            for t in fp_testcases
        ])

        boundary_found = []
        for num in numbers:
            if str(num - 1) in tc_text or str(num) in tc_text or str(num + 1) in tc_text:
                boundary_found.append(num)

        missing = [n for n in numbers if n not in boundary_found]
        if missing:
            issues.append({
                "severity": "严重",
                "check": "边界值覆盖不足",
                "detail": f"{fp_id} ({fp.get('name', '')}) 描述中包含数值 {numbers}，但用例中未覆盖 {missing} 的边界值（±1）",
                "suggestion": f"为数值 {', '.join(str(n) for n in missing)} 补充 N-1, N, N+1 边界用例",
            })

        # range 类型至少应有 3 条用例
        if len(fp_testcases) < 3:
            issues.append({
                "severity": "轻微",
                "check": "边界值用例不足",
                "detail": f"{fp_id} ({fp.get('name', '')}) 为 range 类型，仅有 {len(fp_testcases)} 条用例",
                "suggestion": "range 类型建议至少 3 条用例（下边界、常规值、上边界）",
            })

    return issues


def check_enum_coverage(features, testcases):
    """检查枚举型 FP 是否遍历了所有枚举值"""
    issues = []

    # 从 FP description 中识别枚举模式
    enum_patterns = [
        (re.compile(r'(\d+)\s*种\s*([\u4e00-\u9fa5]+)'), "N种XX模式"),
        (re.compile(r'([一二三四五六七八九十\d]+)\s*个\s*([\u4e00-\u9fa5]+)'), "N个XX模式"),
        (re.compile(r'(Day[1-7]|第[一二三四五六七八九十\d]+天)'), "天数枚举"),
        (re.compile(r'([A-Za-z]+)\s*[×xX]\s*(\d+)\s*种'), "交叉枚举"),
    ]

    for fp in features:
        desc = fp.get("description", "")
        fp_id = fp.get("id", "")
        fp_name = fp.get("name", "")

        # 尝试提取枚举数量
        enum_count = None
        enum_type = None
        for pattern, label in enum_patterns:
            match = pattern.search(desc)
            if match:
                enum_count = int(match.group(1)) if match.group(1).isdigit() else None
                # 中文数字转换
                cn_nums = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}
                if enum_count is None and match.group(1) in cn_nums:
                    enum_count = cn_nums[match.group(1)]
                enum_type = label
                break

        if enum_count is None or enum_count < 2:
            continue

        # 检查该 FP 对应的用例数量
        fp_testcases = [tc for tc in testcases if tc.get("feature_id") == fp_id]

        if len(fp_testcases) < enum_count:
            issues.append({
                "severity": "严重",
                "check": "枚举遍历不足",
                "detail": f"{fp_id} ({fp_name}) 描述中包含 {enum_count} 种{enum_type}，但仅有 {len(fp_testcases)} 条用例",
                "suggestion": f"每种枚举值至少 1 条用例，建议补充至 {enum_count} 条以上",
            })

    return issues


def check_title_duplication(features, testcases):
    """检查用例标题是否重复或高度相似"""
    issues = []

    # 按标题分组
    title_groups = {}
    for tc in testcases:
        title = tc.get("title", "").strip()
        if not title:
            continue
        # 归一化：去空格、转小写
        normalized = re.sub(r"\s+", "", title).lower()
        if normalized not in title_groups:
            title_groups[normalized] = []
        title_groups[normalized].append(tc)

    for normalized, tcs in title_groups.items():
        if len(tcs) > 1:
            ids = ", ".join(tc.get("id", "") for tc in tcs)
            issues.append({
                "severity": "轻微",
                "check": "用例标题重复",
                "detail": f"{ids} 标题完全相同：「{tcs[0].get('title', '')}」",
                "suggestion": "如果测试场景不同，请区分标题；如果场景相同，考虑合并",
            })

    # 检查高度相似（编辑距离小但不同）
    titles = [(tc.get("id", ""), tc.get("title", "").strip()) for tc in testcases if tc.get("title", "").strip()]
    for i in range(len(titles)):
        for j in range(i + 1, len(titles)):
            id1, t1 = titles[i]
            id2, t2 = titles[j]
            if t1 == t2:
                continue  # 完全重复已在上面处理
            # 简单相似度：一个包含另一个
            if len(t1) > 5 and len(t2) > 5 and (t1 in t2 or t2 in t1):
                issues.append({
                    "severity": "提示",
                    "check": "用例标题高度相似",
                    "detail": f"{id1}「{t1}」与 {id2}「{t2}」高度相似",
                    "suggestion": "检查是否为重复用例或可以合并",
                })

    return issues


def check_p0_allocation(features, testcases):
    """检查 P0 分配是否合理：每个状态分支至少 1 条 P0"""
    issues = []

    # 按 FP 分组用例
    fp_testcases = {}
    for tc in testcases:
        fid = tc.get("feature_id", "")
        if fid not in fp_testcases:
            fp_testcases[fid] = []
        fp_testcases[fid].append(tc)

    for fp in features:
        fp_id = fp.get("id", "")
        category = fp.get("category", "")
        tcs = fp_testcases.get(fp_id, [])

        if not tcs:
            continue

        p0_count = sum(1 for tc in tcs if tc.get("priority") == "P0")

        # state 类型：每个状态分支至少 1 条 P0
        if category == "state":
            # 估算状态分支数（从 FP name 中推断）
            fp_name = fp.get("name", "")
            # 如果有多个 FP 共享同一 req_id 且 category=state，说明有多个状态
            same_req_states = [f for f in features if f.get("req_id") == fp.get("req_id") and f.get("category") == "state"]
            if len(same_req_states) > 1 and p0_count == 0:
                issues.append({
                    "severity": "轻微",
                    "check": "P0 分配不足",
                    "detail": f"{fp_id} ({fp_name}) 为 state 类型，{fp.get('req_id', '')} 下有 {len(same_req_states)} 个状态分支，但该分支无 P0 用例",
                    "suggestion": "每个状态分支的边界临界值至少分配 1 条 P0",
                })

        # range 类型：至少 1 条 P0
        if category == "range" and p0_count == 0:
            issues.append({
                "severity": "轻微",
                "check": "P0 分配不足",
                "detail": f"{fp_id} ({fp.get('name', '')}) 为 range 类型但无 P0 用例",
                "suggestion": "数值区间的边界临界值应至少分配 1 条 P0",
            })

    return issues


def check_expected_splitting(features, testcases):
    """检查预期结果是否包含多个检查项但未拆分（检测'并且'/'同时'/'且'连接词）"""
    issues = []
    split_indicators = ["并且", "同时", "且", "；", ";", "，", ","]

    for tc in testcases:
        expected = tc.get("expected_results")
        if expected is None:
            expected = [tc.get("expected_result", "")]
        if not isinstance(expected, list):
            expected = [expected]

        for item in expected:
            item_str = str(item).strip()
            if not item_str:
                continue
            # 检查是否包含多个检查项连接词
            for indicator in split_indicators:
                if indicator in item_str and len(item_str) > 10:
                    issues.append({
                        "severity": "提示",
                        "check": "预期结果未拆分",
                        "detail": f"{tc.get('id', '未知')}: 预期结果中包含「{indicator}」，可能包含多个检查项：「{item_str[:50]}...」",
                        "suggestion": "将多个检查项拆分为独立的预期结果行，以便单独判 P/F 和提 BUG",
                    })
                    break  # 只报告一次

    return issues


def run_review(features_path, testcases_path, output_dir=None):
    if not os.path.exists(features_path):
        print(f"[ERROR] Features file not found: {features_path}", file=sys.stderr)
        sys.exit(1)

    if not os.path.exists(testcases_path):
        print(f"[ERROR] Testcases file not found: {testcases_path}", file=sys.stderr)
        sys.exit(1)

    features_data = load_json(features_path)
    testcases_data = load_json(testcases_path)

    features = features_data.get("features", [])
    testcases = testcases_data.get("testcases", [])

    all_issues = []

    # 运行各项规则检查
    checks = [
        ("覆盖度检查", check_coverage),
        ("完整性检查", check_completeness),
        ("Schema 类型校验", check_schema_types),
        ("编号连续性", check_numbering),
        ("步骤格式", check_step_format),
        ("边界值覆盖", check_boundary_coverage),
        ("枚举遍历", check_enum_coverage),
        ("用例标题重复", check_title_duplication),
        ("P0 分配", check_p0_allocation),
        ("预期结果拆分", check_expected_splitting),
        ("优先级分布", check_priority_distribution),
        ("模糊表述", check_vague_expressions),
        ("预期结果重复", check_expected_results),
    ]

    for check_name, check_func in checks:
        issues = check_func(features, testcases)
        if issues:
            all_issues.extend(issues)

    # 统计
    severity_counts = {"严重": 0, "轻微": 0, "提示": 0}
    for issue in all_issues:
        sev = issue.get("severity", "提示")
        if sev in severity_counts:
            severity_counts[sev] += 1

    result = {
        "review_time": datetime.now().isoformat(),
        "total_features": len(features),
        "total_testcases": len(testcases),
        "total_issues": len(all_issues),
        "severity_summary": severity_counts,
        "issues": all_issues,
    }

    # 生成 Markdown 报告
    md = generate_markdown_report(result)

    if output_dir is None:
        output_dir = os.path.dirname(testcases_path)

    report_path = os.path.join(output_dir, "step5_review_report.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(md)

    # JSON 结果
    json_path = os.path.join(output_dir, "step5_review_result.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"[OK] Review report: {report_path}")
    print(f"[INFO] Total issues: {len(all_issues)} (严重:{severity_counts['严重']} 轻微:{severity_counts['轻微']} 提示:{severity_counts['提示']})")
    return result


def generate_markdown_report(result):
    lines = []
    lines.append("# 测试用例审查报告")
    lines.append("")
    lines.append(f"**审查时间**: {result['review_time']}")
    lines.append(f"**用例总数**: {result['total_testcases']}")
    lines.append(f"**功能点数**: {result['total_features']}")
    lines.append("")

    sev = result["severity_summary"]
    lines.append("## 问题汇总")
    lines.append("")
    lines.append(f"| 严重度 | 数量 |")
    lines.append(f"|--------|------|")
    lines.append(f"| 严重 | {sev['严重']} |")
    lines.append(f"| 轻微 | {sev['轻微']} |")
    lines.append(f"| 提示 | {sev['提示']} |")
    lines.append("")

    sev_sections = {
        "严重": "需修复",
        "轻微": "建议修复",
        "提示": "可选优化",
    }

    issues = result["issues"]
    for sev_level, sev_label in sev_sections.items():
        sev_issues = [i for i in issues if i["severity"] == sev_level]
        if not sev_issues:
            continue

        lines.append(f"## {sev_level}问题 ({sev_label})")
        lines.append("")

        for idx, issue in enumerate(sev_issues, 1):
            lines.append(f"### [{issue['check']}] {issue['detail']}")
            lines.append(f"**建议**: {issue['suggestion']}")
            lines.append("")

    if not issues:
        lines.append("## 审查通过")
        lines.append("")
        lines.append("未发现明显问题。")

    return "\n".join(lines)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python review.py <step3_features.json> <step4_testcases.json> [--output-dir <dir>]", file=sys.stderr)
        sys.exit(1)

    fea = sys.argv[1]
    tcs = sys.argv[2]
    out_dir = None
    if "--output-dir" in sys.argv:
        idx = sys.argv.index("--output-dir")
        if idx + 1 < len(sys.argv):
            out_dir = sys.argv[idx + 1]

    run_review(fea, tcs, out_dir)
