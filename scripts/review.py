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
        ("编号连续性", check_numbering),
        ("步骤格式", check_step_format),
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
