"""
schedule_runtime.py
被定时任务调用的脚本共用的辅助函数：
- 时间窗口判断
- 主动结束"今日剩余触发"（次日自动恢复）
- "今天已经完成过" 的持久化标记
"""

import json
import os
import subprocess
import sys
from datetime import datetime, time
from pathlib import Path


# 日志/标记文件目录
SCRIPT_DIR = Path(__file__).resolve().parent
LOG_DIR = SCRIPT_DIR / "log"


def now() -> datetime:
    return datetime.now()


def in_window(start: time, end: time, current: datetime | None = None) -> bool:
    """判断 current 是否在 [start, end] 闭区间内。支持跨午夜 (e.g. 22:00–02:00)。"""
    cur = (current or now()).time()
    if start <= end:
        return start <= cur <= end
    # 跨午夜: 22:00–02:00 -> cur>=22:00 或 cur<=02:00
    return cur >= start or cur <= end


def task_name_from_env_or_arg() -> str:
    """从命令行第 1 个参数读取任务名（推荐显式传入）。"""
    if len(sys.argv) < 2:
        return ""
    return sys.argv[1]


def flag_path(date: datetime | None = None) -> Path:
    """当日完成标记文件路径: log/done_YYYYMMDD.flag"""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    d = (date or now()).strftime("%Y%m%d")
    return LOG_DIR / f"done_{d}.flag"


def already_done_today() -> bool:
    return flag_path().exists()


def mark_done_today(payload: dict | None = None) -> Path:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    fp = flag_path()
    body = {
        "done_at": now().isoformat(timespec="seconds"),
        "payload": payload or {},
    }
    fp.write_text(json.dumps(body, ensure_ascii=False, indent=2), encoding="utf-8")
    return fp


def clear_today_flag() -> None:
    fp = flag_path()
    if fp.exists():
        fp.unlink()


def end_task_for_today(task_name: str) -> tuple[bool, str]:
    """
    调 schtasks /End: 停止正在运行的实例，并禁用"今日剩余触发"，次日自动恢复。
    返回 (success, message)。
    """
    if not task_name:
        return False, "task_name is empty"
    r = subprocess.run(
        ["schtasks", "/End", "/TN", task_name],
        capture_output=True, text=True
    )
    msg = (r.stdout or r.stderr).strip()
    return r.returncode == 0, msg


def delete_task(task_name: str) -> tuple[bool, str]:
    """
    永久删除任务: schtasks /Delete /TN <name> /F。
    与 end_task_for_today 的区别: /End 是"今天到此为止", /Delete 是"永远删除"。
    """
    if not task_name:
        return False, "task_name is empty"
    r = subprocess.run(
        ["schtasks", "/Delete", "/TN", task_name, "/F"],
        capture_output=True, text=True
    )
    msg = (r.stdout or r.stderr).strip()
    return r.returncode == 0, msg
