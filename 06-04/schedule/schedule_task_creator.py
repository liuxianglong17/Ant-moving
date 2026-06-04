"""
schedule_task_creator.py
从同级目录的 config.json 读取定时任务配置，并在 Windows 任务计划程序中创建任务。
创建成功后，将任务元信息追加到 log/tasks.jsonl，
便于 schedule_task_cleaner.py 后续按条件清理。

config 字段:
  - schedule_mode: "once" | "interval" | "daily"
  - trigger_time: ISO 格式的开始时间 (例如 "2026-06-04T10:00:00")
  - interval_seconds: 当 schedule_mode=interval 时的间隔秒数
  - job_config_path: 指向 job_config.json 的绝对路径

job_config 字段:
  - script_path: 要执行的脚本路径 (.py / .ps1 / .bat / .exe)
  - script_args: 脚本输入参数列表
"""

import json
import os
import sys
import subprocess
import uuid
from datetime import datetime
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
CONFIG_PATH = SCRIPT_DIR / "config.json"
LOG_DIR = SCRIPT_DIR / "log"
LOG_FILE = LOG_DIR / "tasks.jsonl"

# 任务名前缀: 用于在 schtasks 中识别本工具创建的任务
TASK_NAME_PREFIX = "SglangScheduledTask_"


def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def load_job_config(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_command(script_path: str, script_args: list) -> str:
    """根据脚本类型构造可执行的命令行。"""
    ext = Path(script_path).suffix.lower()
    args_str = " ".join(f'"{a}"' for a in script_args)

    if ext == ".py":
        return f'python "{script_path}" {args_str}'
    elif ext == ".ps1":
        return f'powershell -ExecutionPolicy Bypass -File "{script_path}" {args_str}'
    elif ext in (".bat", ".cmd"):
        return f'"{script_path}" {args_str}'
    else:
        return f'"{script_path}" {args_str}'


def append_log(record: dict) -> None:
    """追加一条任务创建记录到 log/tasks.jsonl。"""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def sync_task_name_in_job_config(job_config_path: str, task_name: str) -> None:
    """
    将 job_config.json 的 script_args 中 --task-name <value> 更新为新任务名。
    找不到 --task-name 时, 在 --max-runs 前插入。
    这样下次 creator 跑时, 业务脚本拿到的 --task-name 与最新任务名一致。
    """
    p = Path(job_config_path)
    if not p.exists():
        return
    try:
        with p.open("r", encoding="utf-8") as f:
            jc = json.load(f)
    except (json.JSONDecodeError, OSError):
        return
    args = jc.get("script_args")
    if not isinstance(args, list):
        return
    new_args = []
    replaced = False
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--task-name" and i + 1 < len(args):
            new_args.append(a)
            new_args.append(task_name)
            i += 2
            replaced = True
        else:
            new_args.append(a)
            i += 1
    if replaced:
        jc["script_args"] = new_args
        with p.open("w", encoding="utf-8") as f:
            json.dump(jc, f, ensure_ascii=False, indent=2)
            f.write("\n")


def delete_task(task_name: str) -> bool:
    """删除已存在的任务；返回是否真正删除。"""
    r = subprocess.run(
        ["schtasks", "/Delete", "/TN", task_name, "/F"],
        capture_output=True, text=True
    )
    return r.returncode == 0


def create_task(task_name: str, schedule_mode: str, trigger_time: str,
                interval_seconds: int, command: str) -> None:
    """通过 schtasks 在 Windows 任务计划程序中创建任务。"""
    # 删除同名已存在任务，避免重复
    delete_task(task_name)

    base = ["schtasks", "/Create", "/TN", task_name, "/TR", command, "/F"]

    if schedule_mode == "once":
        start_dt = datetime.fromisoformat(trigger_time)
        st = start_dt.strftime("%H:%M")
        sd = start_dt.strftime("%m/%d/%Y")
        cmd = base + ["/SC", "ONCE", "/ST", st, "/SD", sd]
    elif schedule_mode == "interval":
        minutes = max(1, int(round(interval_seconds / 60)))
        start_dt = datetime.fromisoformat(trigger_time)
        st = start_dt.strftime("%H:%M")
        cmd = base + ["/SC", "MINUTE", "/MO", str(minutes), "/ST", st]
    elif schedule_mode == "daily":
        start_dt = datetime.fromisoformat(trigger_time)
        st = start_dt.strftime("%H:%M")
        cmd = base + ["/SC", "DAILY", "/ST", st]
    else:
        raise ValueError(f"不支持的 schedule_mode: {schedule_mode}")

    print("创建命令:", " ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"创建任务失败: {result.stderr}")
        sys.exit(1)
    print(f"成功创建定时任务: {task_name}")


def main():
    if not CONFIG_PATH.exists():
        print(f"未找到配置文件: {CONFIG_PATH}")
        sys.exit(1)

    config = load_config()
    print("加载 config:", json.dumps(config, ensure_ascii=False, indent=2))

    schedule_mode = config.get("schedule_mode")
    trigger_time = config.get("trigger_time")
    interval_seconds = config.get("interval_seconds", 0)
    job_config_path = config.get("job_config_path")

    if not all([schedule_mode, trigger_time, job_config_path]):
        print("config 缺少必要字段: schedule_mode / trigger_time / job_config_path")
        sys.exit(1)

    job_cfg = load_job_config(job_config_path)
    print("加载 job_config:", json.dumps(job_cfg, ensure_ascii=False, indent=2))

    script_path = job_cfg.get("script_path")
    script_args = job_cfg.get("script_args", [])
    if not script_path:
        print("job_config 缺少 script_path")
        sys.exit(1)

    command = build_command(script_path, script_args)
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    task_name = f"{TASK_NAME_PREFIX}{timestamp}"
    task_uuid = str(uuid.uuid4())

    create_task(task_name, schedule_mode, trigger_time, interval_seconds, command)

    # 把最新任务名回写到 job_config.json 的 --task-name,
    # 防止"鸡生蛋": 业务脚本删任务时拿到的就是当前任务名。
    sync_task_name_in_job_config(job_config_path, task_name)

    # 写日志，便于清理脚本读取
    record = {
        "task_name": task_name,
        "uuid": task_uuid,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "schedule_mode": schedule_mode,
        "trigger_time": trigger_time,
        "interval_seconds": interval_seconds,
        "job_config_path": os.path.abspath(job_config_path),
        "script_path": script_path,
        "script_args": script_args,
        "command": command,
        "creator_dir": str(SCRIPT_DIR),
        "status": "active",
    }
    append_log(record)
    print(f"已记录日志: {LOG_FILE}")

    # 验证任务
    print("\n任务列表验证:")
    verify = subprocess.run(
        ["schtasks", "/Query", "/TN", task_name],
        capture_output=True, text=True
    )
    print(verify.stdout or verify.stderr)


if __name__ == "__main__":
    main()
