"""
debug/create_timestamp_file.py
在脚本所在目录创建文件:
  文件名: HH-MM.txt
  文件内容: 当前执行的时间戳
"""
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent

now = datetime.now()
file_name = now.strftime("%H-%M") + ".txt"
file_path = SCRIPT_DIR / file_name

file_path.write_text(now.isoformat(timespec="seconds"), encoding="utf-8")
print(f"已创建: {file_path}")
