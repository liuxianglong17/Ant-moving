"""
schedule_task_creator.py
从同级目录的 config.json 读取定时任务配置，并在 Windows 任务计划程序中创建任务。
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
from datetime import datetime, timedelta
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
CONFIG_PATH = SCRIPT_DIR / "config.json"


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


def create_task(task_name: str, schedule_mode: str, trigger_time: str,
                interval_seconds: int, command: str) -> None:
    """通过 schtasks 在 Windows 任务计划程序中创建任务。"""
    # 删除同名已存在任务，避免重复
    subprocess.run(
        ["schtasks", "/Delete", "/TN", task_name, "/F"],
        capture_output=True, text=True
    )

    base = ["schtasks", "/Create", "/TN", task_name, "/TR", command, "/F"]

    if schedule_mode == "once":
        # 一次性任务：/SC ONCE /ST start_time
        start_dt = datetime.fromisoformat(trigger_time)
        st = start_dt.strftime("%H:%M")
        sd = start_dt.strftime("%m/%d/%Y")
        cmd = base + ["/SC", "ONCE", "/ST", st, "/SD", sd]
    elif schedule_mode == "interval":
        # schtasks 不支持"每 N 秒重复"，但支持 /SC MINUTE /MO n (n>=1)
        # interval_seconds < 60 视作 1 分钟; >= 60 时换算为分钟数
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
    if result.returncode == 0:
        print(f"成功创建定时任务: {task_name}")
    else:
        print(f"创建任务失败: {result.stderr}")
        sys.exit(1)

    # 如果是 interval 模式，输出说明
    if schedule_mode == "interval":
        print(
            f"注: 间隔模式以每日任务方式创建，间隔 {interval_seconds} 秒。"
            "如需严格 N 秒循环，建议改用 Python 内部 sleep 循环或 Windows 计划任务高级设置。"
        )


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
    task_name = f"SglangScheduledTask_{datetime.now().strftime('%Y%m%d%H%M%S')}"

    create_task(task_name, schedule_mode, trigger_time, interval_seconds, command)

    # 验证任务
    print("\n任务列表验证:")
    verify = subprocess.run(
        ["schtasks", "/Query", "/TN", task_name],
        capture_output=True, text=True
    )
    print(verify.stdout or verify.stderr)


if __name__ == "__main__":
    main()
