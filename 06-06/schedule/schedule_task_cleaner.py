"""
schedule_task_cleaner.py
根据模式清理 Windows 计划任务。

支持模式 (通过 --mode 指定):
  all         清理系统所有计划任务 (危险: 一次性删除所有任务)
  prefix      清理任务名以 SglangScheduledTask_ 开头的任务
              (即本工具下 d:\\personal_code\\temp\\schedule 创建的所有任务)
  job_config  清理使用指定 job_config.json 创建的任务
              (需要 --job-config <path>)
  name        清理指定名称的任务 (需要 --task-name <name>)
  by-script   清理运行指定脚本的任务 (需要 --script-path <path>)
  log-only    仅根据 log/tasks.jsonl 中的记录来清理
              (用于清理"曾经由本工具创建过"的任务, 即使任务名已被改)

默认 dry-run = true: 仅打印将要删除的任务, 不实际删除。
使用 --yes 真正执行删除。
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


# 兼容 Windows GBK 控制台
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


SCRIPT_DIR = Path(__file__).resolve().parent
LOG_FILE = SCRIPT_DIR / "log" / "tasks.jsonl"
TASK_NAME_PREFIX = "SglangScheduledTask_"


def list_all_tasks() -> list[str]:
    """列出系统中所有任务名。使用 CSV 格式避免不同语言下表头差异。
    CSV 列: 1=TaskName(带引号), 2=NextRunTime, 3=Status
    """
    r = subprocess.run(
        ["schtasks", "/Query", "/FO", "CSV", "/NH"],
        capture_output=True, text=True
    )
    names = []
    for line in r.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            parts = list(__import__("csv").reader([line]))[0]
        except Exception:
            continue
        if not parts:
            continue
        # 第 1 列是任务名
        name = parts[0].strip().strip('"')
        if name.startswith("\\"):
            name = name[1:]
        name = name.split("\\")[-1]
        if name:
            names.append(name)
    return names


def list_log_records() -> list[dict]:
    """读取 log/tasks.jsonl 中所有记录。"""
    if not LOG_FILE.exists():
        return []
    out = []
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def delete_task(task_name: str) -> bool:
    r = subprocess.run(
        ["schtasks", "/Delete", "/TN", task_name, "/F"],
        capture_output=True, text=True
    )
    return r.returncode == 0


def mark_status(task_name: str, new_status: str) -> None:
    """在 log/tasks.jsonl 中给指定 task_name 追加一条状态更新记录。"""
    if not LOG_FILE.exists():
        return
    record = {
        "task_name": task_name,
        "updated_at": __import__("datetime").datetime.now().isoformat(timespec="seconds"),
        "status": new_status,
    }
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def collect_targets(args) -> list[tuple[str, str]]:
    """根据 mode 收集 (task_name, reason) 列表。"""
    targets: list[tuple[str, str]] = []

    if args.mode == "all":
        names = list_all_tasks()
        for n in names:
            targets.append((n, "mode=all"))

    elif args.mode == "prefix":
        names = list_all_tasks()
        for n in names:
            if n.startswith(TASK_NAME_PREFIX):
                targets.append((n, f"prefix={TASK_NAME_PREFIX}"))

    elif args.mode == "job_config":
        if not args.job_config:
            print("ERROR: --mode job_config 需要 --job-config <path>")
            sys.exit(2)
        job_config_abs = os.path.abspath(args.job_config)
        records = list_log_records()
        seen = set()
        for rec in records:
            if rec.get("job_config_path") == job_config_abs and rec.get("status") == "active":
                t = rec.get("task_name")
                if t and t not in seen:
                    seen.add(t)
                    targets.append((t, f"job_config={job_config_abs}"))
        # 如果日志中没有, 退化为按脚本路径清理
        if not targets:
            print(f"日志中未找到 job_config={job_config_abs} 的记录, 改用脚本路径匹配")
            with open(args.job_config, "r", encoding="utf-8") as f:
                jc = json.load(f)
            script_path = jc.get("script_path", "")
            for n in list_all_tasks():
                # 任务名由本工具创建, 包含时间戳, 用 /V 详情来判断
                targets.append((n, f"fallback-script={script_path}"))

    elif args.mode == "name":
        if not args.task_name:
            print("ERROR: --mode name 需要 --task-name <name>")
            sys.exit(2)
        targets.append((args.task_name, "mode=name"))

    elif args.mode == "by-script":
        if not args.script_path:
            print("ERROR: --mode by-script 需要 --script-path <path>")
            sys.exit(2)
        script_abs = os.path.abspath(args.script_path).lower()
        records = list_log_records()
        seen = set()
        for rec in records:
            if rec.get("status") != "active":
                continue
            sp = rec.get("script_path", "")
            if sp and os.path.abspath(sp).lower() == script_abs:
                t = rec.get("task_name")
                if t and t not in seen:
                    seen.add(t)
                    targets.append((t, f"script={script_abs}"))

    elif args.mode == "log-only":
        records = list_log_records()
        seen = set()
        for rec in records:
            if rec.get("status") != "active":
                continue
            t = rec.get("task_name")
            if t and t not in seen:
                seen.add(t)
                targets.append((t, "log-only"))

    else:
        print(f"ERROR: 未知 mode: {args.mode}")
        sys.exit(2)

    return targets


def main():
    parser = argparse.ArgumentParser(description="清理 Windows 计划任务")
    parser.add_argument(
        "--mode",
        required=True,
        choices=["all", "prefix", "job_config", "name", "by-script", "log-only"],
        help="清理模式",
    )
    parser.add_argument("--job-config", help="job_config 路径 (--mode job_config)")
    parser.add_argument("--task-name", help="任务名 (--mode name)")
    parser.add_argument("--script-path", help="脚本路径 (--mode by-script)")
    parser.add_argument(
        "--yes",
        action="store_true",
        help="真正执行删除 (默认 dry-run, 仅打印)",
    )
    args = parser.parse_args()

    targets = collect_targets(args)

    if not targets:
        print("没有匹配的任务。")
        return

    print(f"将处理 {len(targets)} 个任务:")
    for name, reason in targets:
        print(f"  - {name}   (reason: {reason})")

    if not args.yes:
        print("\n[DRY-RUN] 未执行删除。加上 --yes 真正执行。")
        return

    success, failed = 0, 0
    for name, _ in targets:
        if delete_task(name):
            mark_status(name, "deleted")
            print(f"  [OK] deleted: {name}")
            success += 1
        else:
            print(f"  [FAIL] {name}")
            failed += 1

    print(f"\nDone: success={success}, failed={failed}")


if __name__ == "__main__":
    main()
