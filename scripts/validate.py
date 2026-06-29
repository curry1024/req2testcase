"""
工作流产物校验与恢复脚本
用途：检查各步骤产物是否存在、格式是否合法，支持断点恢复

用法:
  python validate.py check <work_dir>                    # 检查当前工作目录所有产物
  python validate.py check <work_dir> --step <N>         # 检查到第 N 步为止
  python validate.py resume <work_dir>                   # 输出应从哪一步恢复
  python validate.py clean <work_dir>                    # 清理损坏的产物（保留上一步）
"""
import json
import sys
import os
from pathlib import Path
from datetime import datetime


# 各步骤产物定义
STEP_ARTIFACTS = {
    1: {
        "name": "Step1: 需求输入",
        "files": ["step1_raw_content.txt"],
        "required": True,
    },
    2: {
        "name": "Step2: 需求解析",
        "files": ["step2_requirements.json"],
        "json_schema": "$schema",
        "required": True,
    },
    3: {
        "name": "Step3: 功能点分解",
        "files": ["step3_features.json", "step3_features.xmind"],
        "json_schema": "$schema",
        "json_file": "step3_features.json",
        "required": True,
    },
    4: {
        "name": "Step4: 用例生成",
        "files": ["step4_testcases.json", "step4_testcases.xlsx"],
        "json_schema": "$schema",
        "json_file": "step4_testcases.json",
        "required": True,
    },
    5: {
        "name": "Step5: 用例审查",
        "files": ["step5_review_report.md", "step5_review_result.json"],
        "json_schema": None,
        "required": False,
    },
    6: {
        "name": "Step6: 最终输出",
        "files": [],
        "required": False,
    },
}

# JSON Schema 验证规则
JSON_VALIDATION = {
    "step2_requirements.json": {
        "required_keys": ["meta", "requirements"],
        "array_keys": ["requirements"],
    },
    "step3_features.json": {
        "required_keys": ["meta", "features"],
        "array_keys": ["features"],
    },
    "step4_testcases.json": {
        "required_keys": ["meta", "testcases"],
        "array_keys": ["testcases"],
    },
}


def check_file_exists(filepath):
    """检查文件是否存在且非空"""
    if not os.path.exists(filepath):
        return False, "文件不存在"
    size = os.path.getsize(filepath)
    if size == 0:
        return False, "文件为空(0字节)"
    return True, f"OK ({size} bytes)"


def check_json_valid(filepath):
    """检查 JSON 文件是否合法"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        return True, data
    except json.JSONDecodeError as e:
        return False, f"JSON 解析失败: {e}"
    except Exception as e:
        return False, f"读取失败: {e}"


def check_json_schema(filepath, rules):
    """检查 JSON 是否符合预期 Schema"""
    valid, data = check_json_valid(filepath)
    if not valid:
        return False, data

    issues = []

    # 检查必需字段
    for key in rules.get("required_keys", []):
        if key not in data:
            issues.append(f"缺少必需字段: {key}")

    # 检查数组字段
    for key in rules.get("array_keys", []):
        if key in data and not isinstance(data[key], list):
            issues.append(f"字段 {key} 应为数组，实际为 {type(data[key]).__name__}")
        elif key in data and len(data[key]) == 0:
            issues.append(f"字段 {key} 为空数组")

    if issues:
        return False, "; ".join(issues)
    return True, data


def check_step(work_dir, step_num):
    """检查某一步的产物"""
    step = STEP_ARTIFACTS.get(step_num)
    if not step:
        return None

    results = {
        "step": step_num,
        "name": step["name"],
        "files": {},
        "status": "ok",
        "issues": [],
    }

    for filename in step["files"]:
        filepath = os.path.join(work_dir, filename)
        exists, msg = check_file_exists(filepath)
        results["files"][filename] = {"exists": exists, "msg": msg}

        if not exists and step["required"]:
            results["status"] = "missing"
            results["issues"].append(f"{filename}: {msg}")

    # JSON Schema 校验
    json_file = step.get("json_file")
    if json_file and json_file in JSON_VALIDATION:
        filepath = os.path.join(work_dir, json_file)
        if os.path.exists(filepath):
            valid, detail = check_json_schema(filepath, JSON_VALIDATION[json_file])
            if not valid:
                results["status"] = "invalid"
                results["issues"].append(f"{json_file}: {detail}")

    return results


def find_resume_step(work_dir):
    """找到应从哪一步恢复"""
    last_ok = 0
    for step_num in sorted(STEP_ARTIFACTS.keys()):
        result = check_step(work_dir, step_num)
        if result and result["status"] == "ok":
            last_ok = step_num
        else:
            break
    return last_ok


def run_check(work_dir, max_step=None):
    """运行完整检查"""
    if not os.path.isdir(work_dir):
        print(f"[ERROR] 工作目录不存在: {work_dir}", file=sys.stderr)
        sys.exit(1)

    print(f"工作流产物检查: {work_dir}")
    print(f"检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 60)

    all_ok = True
    for step_num in sorted(STEP_ARTIFACTS.keys()):
        if max_step and step_num > max_step:
            break

        result = check_step(work_dir, step_num)
        if not result:
            continue

        status_icon = "[OK]" if result["status"] == "ok" else "[FAIL]"
        print(f"\n{status_icon} {result['name']}")

        for filename, info in result["files"].items():
            icon = "  [OK]" if info["exists"] else "  [MISS]"
            print(f"  {icon} {filename}: {info['msg']}")

        if result["issues"]:
            all_ok = False
            for issue in result["issues"]:
                print(f"  [WARN] {issue}")

    print("\n" + "-" * 60)
    resume_step = find_resume_step(work_dir)
    if resume_step == 0:
        print("状态: 无有效产物，需从 Step1 重新开始")
    elif resume_step < max(STEP_ARTIFACTS.keys()):
        print(f"状态: Step1~{resume_step} 产物正常，可从 Step{resume_step + 1} 继续")
    else:
        print("状态: 所有步骤已完成")

    return all_ok


def run_resume(work_dir):
    """输出恢复建议"""
    if not os.path.isdir(work_dir):
        print(f"[ERROR] 工作目录不存在: {work_dir}", file=sys.stderr)
        sys.exit(1)

    resume_step = find_resume_step(work_dir)
    next_step = resume_step + 1

    if resume_step == 0:
        print(f"RESUME_STEP=0")
        print(f"# 无有效产物，需从 Step1 重新开始")
    elif next_step <= max(STEP_ARTIFACTS.keys()):
        print(f"RESUME_STEP={next_step}")
        print(f"# Step1~{resume_step} 产物正常，可从 Step{next_step} 继续")
    else:
        print(f"RESUME_STEP=done")
        print(f"# 所有步骤已完成")


def run_clean(work_dir):
    """清理损坏的产物（保留最后一步有效的）"""
    resume_step = find_resume_step(work_dir)

    if resume_step == 0:
        print("[WARN] 无有效产物，将清理整个目录")
        for step_num in sorted(STEP_ARTIFACTS.keys()):
            for filename in STEP_ARTIFACTS[step_num]["files"]:
                filepath = os.path.join(work_dir, filename)
                if os.path.exists(filepath):
                    os.remove(filepath)
                    print(f"  已删除: {filename}")
    else:
        print(f"[INFO] 保留 Step1~{resume_step} 产物，清理后续步骤")
        for step_num in sorted(STEP_ARTIFACTS.keys()):
            if step_num <= resume_step:
                continue
            for filename in STEP_ARTIFACTS[step_num]["files"]:
                filepath = os.path.join(work_dir, filename)
                if os.path.exists(filepath):
                    os.remove(filepath)
                    print(f"  已删除: {filename}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python validate.py <check|resume|clean> <work_dir> [--step N]", file=sys.stderr)
        sys.exit(1)

    command = sys.argv[1]
    work_dir = sys.argv[2]
    max_step = None

    if "--step" in sys.argv:
        idx = sys.argv.index("--step")
        if idx + 1 < len(sys.argv):
            max_step = int(sys.argv[idx + 1])

    if command == "check":
        ok = run_check(work_dir, max_step)
        sys.exit(0 if ok else 1)
    elif command == "resume":
        run_resume(work_dir)
    elif command == "clean":
        run_clean(work_dir)
    else:
        print(f"Unknown command: {command}", file=sys.stderr)
        sys.exit(1)
