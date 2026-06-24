"""
增量合并脚本
将新生成的用例合并到现有用例中，保留已审核内容

规则:
- 相同 feature_id: 保留旧数据
- 新功能点: 追加到末尾，ID 递增
- 旧功能点已废弃: 标记 notes

用法: python merge_testcases.py --existing <旧JSON> --new <新JSON> --output <输出路径>
"""
import json
import sys
import os
import argparse
import copy


def load_json(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def get_max_tc_number(testcases):
    max_num = 0
    for tc in testcases:
        tid = tc.get("id", "TC-000")
        if tid.startswith("TC-"):
            try:
                num = int(tid[3:])
                max_num = max(max_num, num)
            except ValueError:
                pass
    return max_num


def merge_testcases(existing_path, new_path, output_path):
    existing_data = load_json(existing_path)
    new_data = load_json(new_path)

    existing_tcs = existing_data.get("testcases", [])
    new_tcs = new_data.get("testcases", [])

    # 旧用例按 feature_id 索引
    existing_by_fid = {}
    for tc in existing_tcs:
        fid = tc.get("feature_id", "")
        if fid:
            existing_by_fid.setdefault(fid, []).append(tc)

    # 新用例按 feature_id 索引
    new_by_fid = {}
    for tc in new_tcs:
        fid = tc.get("feature_id", "")
        if fid:
            new_by_fid.setdefault(fid, []).append(tc)

    merged = []

    # 处理：旧有 + 新无 → 标记废弃
    for fid, tcs in existing_by_fid.items():
        if fid not in new_by_fid:
            for tc in tcs:
                tc_copy = copy.deepcopy(tc)
                old_notes = tc_copy.get("notes", "")
                if "[已废弃]" not in old_notes:
                    tc_copy["notes"] = f"[已废弃] {old_notes}".strip()
                merged.append(tc_copy)

    # 处理：新旧都有 → 保留旧数据
    for fid, tcs in existing_by_fid.items():
        if fid in new_by_fid:
            for tc in tcs:
                merged.append(copy.deepcopy(tc))

    # 处理：新有 + 旧无 → 追加
    max_num = get_max_tc_number(merged)
    for fid, tcs in new_by_fid.items():
        if fid not in existing_by_fid:
            for tc in tcs:
                max_num += 1
                tc_copy = copy.deepcopy(tc)
                tc_copy["id"] = f"TC-{max_num:03d}"
                merged.append(tc_copy)

    # 重新编号确保连续
    for i, tc in enumerate(merged):
        tc["id"] = f"TC-{i+1:03d}"

    summary = {
        "preserved": sum(1 for fid in existing_by_fid if fid in new_by_fid),
        "deprecated": sum(1 for fid in existing_by_fid if fid not in new_by_fid),
        "added": sum(1 for fid in new_by_fid if fid not in existing_by_fid),
    }

    result = {
        "$schema": "testcases-v1",
        "meta": {
            "total_testcases": len(merged),
            "merge_summary": summary,
        },
        "testcases": merged,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"[OK] Merged: {output_path}")
    print(f"[INFO] Total: {len(merged)} (保留:{summary['preserved']} 废弃:{summary['deprecated']} 新增:{summary['added']})")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Merge existing and new testcase JSON files")
    parser.add_argument("--existing", required=True)
    parser.add_argument("--new", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    merge_testcases(args.existing, args.new, args.output)
