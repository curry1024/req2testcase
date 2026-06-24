"""
XMind 脑图生成脚本
输入: step3_features.json (功能点数据)
输出: step3_features.xmind (XMind 2020+ 格式脑图)

用法: python generate_xmind.py <features_json_path> [output_path]
"""
import json
import zipfile
import uuid
import os
import sys
from datetime import datetime


def generate_topic_id():
    return str(uuid.uuid4())


def feature_to_topic(fp):
    """将一条 feature point 转为 XMind topic 节点（只写场景描述，不写用例细节）"""
    title = f"{fp.get('name', fp.get('id', ''))}"
    topic = {
        "id": generate_topic_id(),
        "class": "topic",
        "title": title,
        "children": {"attached": []},
    }
    return topic


def req_to_topic(req_id, module, feature_name, features):
    """将一条 REQ 及其子功能点转为 XMind topic 节点"""
    req_title = f"{req_id}: {feature_name}"
    topic = {
        "id": generate_topic_id(),
        "class": "topic",
        "title": req_title,
        "children": {"attached": []},
    }

    for fp in features:
        if fp.get("req_id") == req_id:
            topic["children"]["attached"].append(feature_to_topic(fp))

    return topic


def module_to_topic(module_name, features):
    """将模块及其子 REQ 和功能点转为 XMind topic 节点"""
    topic = {
        "id": generate_topic_id(),
        "class": "topic",
        "title": f"模块: {module_name}",
        "children": {"attached": []},
    }

    # 找出该模块下所有 REQ
    req_map = {}
    for fp in features:
        rid = fp.get("req_id", "")
        rname = fp.get("requirement_name", "未命名需求")

        if rid not in req_map:
            req_map[rid] = {"name": rname, "features": []}
        req_map[rid]["features"].append(fp)

    for rid, rdata in req_map.items():
        topic["children"]["attached"].append(
            req_to_topic(rid, module_name, rdata["name"], rdata["features"])
        )

    return topic


def build_content_json(data):
    features = data.get("features", [])
    source = data.get("meta", {}).get("source_file", "需求文档")

    # 按 module 分组
    module_map = {}
    for fp in features:
        mod = fp.get("module", "未分类")
        if mod not in module_map:
            module_map[mod] = []
        module_map[mod].append(fp)

    # 根节点
    root = {
        "id": generate_topic_id(),
        "class": "topic",
        "title": source,
        "structureClass": "org.xmind.ui.map.unbalanced",
        "children": {"attached": []},
    }

    for mod_name, mod_features in module_map.items():
        root["children"]["attached"].append(
            module_to_topic(mod_name, mod_features)
        )

    # 统计标签
    total = len(features)

    # 汇总节点
    summary = {
        "id": generate_topic_id(),
        "class": "topic",
        "title": f"共 {total} 个测试场景",
        "children": {"attached": []},
    }
    root["children"]["attached"].append(summary)

    content = [{
        "id": generate_topic_id(),
        "class": "sheet",
        "title": "功能点分解",
        "rootTopic": root,
    }]

    return content


def build_metadata_json():
    return {
        "creator": {
            "name": "TestCase_QA",
            "version": "1.0.0"
        },
        "created": datetime.now().isoformat(),
    }


def build_manifest_json():
    return {
        "file-entries": {
            "content.json": {},
            "metadata.json": {},
        }
    }


def generate_xmind(features_json_path, output_path=None):
    if not os.path.exists(features_json_path):
        print(f"[ERROR] File not found: {features_json_path}", file=sys.stderr)
        sys.exit(1)

    with open(features_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if output_path is None:
        output_path = features_json_path.replace(".json", ".xmind")

    content = build_content_json(data)
    metadata = build_metadata_json()
    manifest = build_manifest_json()

    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("content.json", json.dumps(content, ensure_ascii=False, indent=2))
        zf.writestr("metadata.json", json.dumps(metadata, ensure_ascii=False, indent=2))
        zf.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))

    total = data.get("meta", {}).get("total_features", len(data.get("features", [])))
    print(f"[OK] XMind generated: {output_path}")
    print(f"[INFO] Total feature points: {total}")
    return output_path


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python generate_xmind.py <features_json_path> [output_path]", file=sys.stderr)
        sys.exit(1)

    out = sys.argv[2] if len(sys.argv) > 2 else None
    generate_xmind(sys.argv[1], out)
