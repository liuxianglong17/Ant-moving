schedule
========

用于 **创建、观察、清理 Windows 计划任务**（基于 `schtasks`）的小工具集。
所有通过本工具创建的任务都会带前缀 `SglangScheduledTask_`，便于按前缀批量识别和清理；
创建器会向 `log/tasks.jsonl` 追加一条 JSONL 审计记录，清理器可据此回读。

工具集还附带一个运行时辅助模块 `schedule_runtime.py`，供被定时任务调用的“业务脚本”使用：
时间窗口判断、“今日已完成”标记、主动结束当日触发（`schtasks /End`）或永久删除任务
（`schtasks /Delete`）。

---

1. 文件一览
-----------

| 文件 | 作用 |
|---|---|
| `schedule_task_creator.py` | 读取 `config.json` + `job_config.json` 在 Windows 任务计划程序中创建任务；创建后追加记录到 `log/tasks.jsonl`。 |
| `schedule_task_cleaner.py` | 按多种模式删除任务：`all` / `prefix` / `job_config` / `name` / `by-script` / `log-only`。默认 dry-run。 |
| `schedule_runtime.py` | 业务脚本侧可 import 的辅助函数：时间窗口、done 标记、`end_task_for_today`、`delete_task`。 |
| `config.json` | 顶层配置：调度模式 + 触发时间 + 指向 `job_config.json` 的路径。 |
| `job_config.json` | 实际要执行的内容：`script_path` + `script_args`。 |
| `test_load.py` | 自检脚本：加载两份配置并打印构造的命令。 |
| `debug/` | 独立的示例 job 脚本（详见其 README）。 |
| `log/tasks.jsonl` | 每次创建任务的追加记录。 |
| `log/runs_YYYY-MM-DD.jsonl` | 示例 job 写入的当日运行计数。 |
| `log/done_YYYYMMDD.flag` | 示例 job 写入的“今日完成”标记。 |

---

2. 快速开始
-----------

### 2.1 改配置

在本目录下编辑两份 JSON。

**`config.json`**（什么时候触发、怎么触发）：

```json
{
  "schedule_mode": "interval",          // "once" | "interval" | "daily"
  "trigger_time": "2026-06-04T13:25:00", // ISO 格式的开始时间
  "interval_seconds": 60,                // 仅 schedule_mode="interval" 时使用
  "job_config_path": "d:\\personal_code\\temp\\schedule\\job_config.json"
}
```

**`job_config.json`**（要跑什么）：

```json
{
  "script_path": "C:\\Users\\Administrator\\AppData\\Local\\Programs\\Python\\Python314\\python.exe",
  "script_args": [
    "d:\\personal_code\\temp\\schedule\\debug\\create_timestamp_with_limit.py",
    "--task-name", "SglangScheduledTask_20260604142903",
    "--max-runs",  "0"
  ]
}
```

> `--max-runs 0` 表示**不限制**（默认），任务会按 schedule 一直触发；改成正整数 N 则运行 N 次后调用 `schtasks /Delete` 自删。详见 `debug/Readme-zh.txt` §2。

`script_path` 支持 `.py` / `.ps1` / `.bat` / `.cmd` / 任意 `.exe`，创建器会按类型
拼出对应的 `schtasks /TR` 命令。

### 2.2 创建任务

```powershell
python schedule_task_creator.py
```

任务名自动生成：`SglangScheduledTask_YYYYMMDDhhmmss`（不带随机后缀，详见 §6
关于重名的说明）。同时会把任务名回写到 `job_config.json` 的 `--task-name`
位置，让业务脚本拿到当前真实任务名。

创建后会向 `log/tasks.jsonl` 追加一条：

```json
{"task_name":"SglangScheduledTask_...","uuid":"...","created_at":"...","schedule_mode":"...","job_config_path":"...","status":"active"}
```

### 2.3 清理任务

```powershell
# 默认 dry-run，只打印将要删除的任务
python schedule_task_cleaner.py --mode prefix

# 真正删除
python schedule_task_cleaner.py --mode prefix --yes

# 删某个 job 的所有任务
python schedule_task_cleaner.py --mode job_config --job-config .\job_config.json --yes

# 删光系统所有任务（危险）
python schedule_task_cleaner.py --mode all --yes
```

---

3. `schedule_task_creator.py` — 支持的调度模式
-----------------------------------------------

| `schedule_mode` | `schtasks` 行为 | 关键字段 |
|---|---|---|
| `once`     | 在 `trigger_time` 触发一次        | `trigger_time` |
| `interval` | 从 `trigger_time` 起每 `interval_seconds` 触发 | `trigger_time`, `interval_seconds`（四舍五入到分钟，最小 1） |
| `daily`    | 每天在 `trigger_time` 的时刻触发  | `trigger_time` |

如果同名任务已存在，创建器会先 `schtasks /Delete` 再重建，**所以重复执行创建器是幂等的**。

---

4. `schedule_task_cleaner.py` — 清理模式
---------------------------------------

| 模式 | 删什么 | 额外参数 |
|---|---|---|
| `all`        | 系统全部计划任务 | – |
| `prefix`     | 任务名前缀为 `SglangScheduledTask_` 的全部任务 | – |
| `job_config` | 在 `tasks.jsonl` 里绑定到指定 `job_config_path` 的任务 | `--job-config` |
| `name`       | 指定名字的单个任务 | `--task-name` |
| `by-script`  | 在 `tasks.jsonl` 里 `script_path` 匹配的活跃任务 | `--script-path` |
| `log-only`   | `tasks.jsonl` 里 `status=active` 的全部任务（覆盖任务被改名的情况） | – |

默认 **dry-run**，加 `--yes` 才会真正删。删除成功时，会在 `tasks.jsonl`
里追加一条 `status: deleted` 记录。

---

5. `schedule_runtime.py` — 业务脚本侧的辅助函数
----------------------------------------------

业务脚本里加一行 `sys.path` 即可 import：

```python
sys.path.insert(0, r"d:\personal_code\temp\schedule")
from schedule_runtime import (
    in_window, now, already_done_today, mark_done_today,
    end_task_for_today, delete_task, clear_today_flag,
)
```

典型用法：

```python
# 1) 时间窗口守卫
if not in_window(dtime(5, 30), dtime(23, 30)):
    return

# 2) “今日已完成” 守卫
if already_done_today():
    return

# 3) 跑业务...

# 4) 业务说“今天可以收工了”
mark_done_today({"reason": "all branches fetched"})
ok, msg = end_task_for_today(args.task_name)  # schtasks /End → 次日自动恢复
```

`end_task_for_today` 调的是 `schtasks /End`：**停掉今日剩余触发**但不删除任务，
第二天按原计划继续。`delete_task` 调 `schtasks /Delete` 才是永久删除。

---

6. 关于“看起来像随机值”的任务名
------------------------------

任务名是 `SglangScheduledTask_YYYYMMDDhhmmss`（**不带随机后缀**）。如果你在同一
秒内重复创建，名字会撞；创建器会先 `schtasks /Delete` 旧任务再创建，外部表现就是
“旧任务被新任务覆盖”。如果想保证同秒也唯一，可以在 job config 里手动加随机
后缀；清理器同时支持按日志清理（`--mode log-only`、`--mode by-script`），
改名后也不会影响清理。

---

7. `debug/` 子目录
------------------

`debug/` 里放了一组独立的示例 job 脚本，集中演示了上面那些 helper 的用法，
详见 `debug/Readme-zh.txt`。
