"""仅验证 config/job_config 加载和命令构造逻辑。"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from schedule_task_creator import load_config, load_job_config, build_command

cfg = load_config()
print("config =", json.dumps(cfg, ensure_ascii=False, indent=2))

job_cfg = load_job_config(cfg["job_config_path"])
print("job_config =", json.dumps(job_cfg, ensure_ascii=False, indent=2))

cmd = build_command(job_cfg["script_path"], job_cfg["script_args"])
print("command =", cmd)
