"""
变更前自动备份脚本
将工作目录中的 .json 文件备份到 backups/<时间戳>/

用法: python backup.py <工作目录路径>
"""
import sys
import os
import shutil
import glob
from datetime import datetime


def backup_workdir(workdir_path):
    if not os.path.isdir(workdir_path):
        print(f"[ERROR] Not a directory: {workdir_path}", file=sys.stderr)
        sys.exit(1)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    backup_dir = os.path.join(workdir_path, "backups", timestamp)
    os.makedirs(backup_dir, exist_ok=True)

    json_files = glob.glob(os.path.join(workdir_path, "*.json"))
    if not json_files:
        print("[INFO] No JSON files to backup")
        return backup_dir

    for f in json_files:
        basename = os.path.basename(f)
        shutil.copy2(f, os.path.join(backup_dir, basename))

    print(f"[OK] Backed up {len(json_files)} files to: {backup_dir}")

    # 清理旧备份（保留最近 10 个）
    backups_root = os.path.join(workdir_path, "backups")
    all_backups = sorted(
        [d for d in os.listdir(backups_root) if os.path.isdir(os.path.join(backups_root, d))],
        reverse=True,
    )

    to_remove = all_backups[10:]
    for old in to_remove:
        shutil.rmtree(os.path.join(backups_root, old), ignore_errors=True)
        print(f"[INFO] Cleaned old backup: {old}")

    if to_remove and len(to_remove) > 0:
        print(f"[INFO] Removed {len(to_remove)} old backup(s), keeping latest 10")

    return backup_dir


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python backup.py <workdir_path>", file=sys.stderr)
        sys.exit(1)

    backup_workdir(sys.argv[1])
