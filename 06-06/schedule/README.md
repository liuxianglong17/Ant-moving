# schedule

A small toolkit for **creating, observing, and cleaning up Windows scheduled tasks**
(via `schtasks`). All scripts use the prefix `SglangScheduledTask_` so they can be
identified and cleaned up in bulk, and the creator writes a JSONL audit log
(`log/tasks.jsonl`) that the cleaner can read back.

The toolkit also ships a runtime helper (`schedule_runtime.py`) for the job
scripts themselves: time-window checks, "done-today" flag, and helpers to
*stop today's remaining triggers* (`schtasks /End`) or *permanently delete*
the task (`schtasks /Delete`).

---

## 1. Files at a glance

| file | role |
|---|---|
| `schedule_task_creator.py` | Create a Windows scheduled task from `config.json` + `job_config.json`; append a record to `log/tasks.jsonl`. |
| `schedule_task_cleaner.py` | Delete tasks in several modes: `all`, `prefix`, `job_config`, `name`, `by-script`, `log-only`. Default is dry-run. |
| `schedule_runtime.py` | Helpers imported by the *job* script: time window, today-flag, `end_task_for_today`, `delete_task`. |
| `config.json` | Top-level config: schedule mode + trigger time + path to a `job_config.json`. |
| `job_config.json` | What to actually run: `script_path` + `script_args`. |
| `test_load.py` | Smoke test: load both configs and print the constructed command. |
| `debug/` | Independent sample job scripts (see its own README). |
| `log/tasks.jsonl` | Append-only record of every task created by this toolkit. |
| `log/runs_YYYY-MM-DD.jsonl` | Per-day run counter (written by sample jobs). |
| `log/done_YYYYMMDD.flag` | "Today is done" marker (written by the window-control sample). |

---

## 2. Quick start

### 2.1 Configure

Edit two JSON files in this directory.

**`config.json`** (when and how to trigger):

```json
{
  "schedule_mode": "interval",          // "once" | "interval" | "daily"
  "trigger_time": "2026-06-04T13:25:00", // ISO start time
  "interval_seconds": 60,                // only used when schedule_mode="interval"
  "job_config_path": "d:\\personal_code\\temp\\schedule\\job_config.json"
}
```

**`job_config.json`** (what to run):

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

> `--max-runs 0` means **unlimited** (the new default) — the task keeps firing on its schedule. Set a positive integer N to auto-delete via `schtasks /Delete` after N invocations. See `debug/README.md` §2.

`script_path` may be `.py`, `.ps1`, `.bat`/`.cmd`, or any `.exe`. The creator
builds the right `schtasks /TR` string for each type.

### 2.2 Create the task

```powershell
python schedule_task_creator.py
```

The task name is auto-generated as
`SglangScheduledTask_YYYYMMDDhhmmss` (so a random timestamp is appended to
avoid collisions if you create the same task twice — see §6 for collision
notes). It is also written back into `job_config.json`'s `--task-name` slot
so the job script knows the live task name.

A record is appended to `log/tasks.jsonl`:

```json
{"task_name":"SglangScheduledTask_...","uuid":"...","created_at":"...","schedule_mode":"...","job_config_path":"...","status":"active"}
```

### 2.3 Clean up

```powershell
# dry-run by default - shows what WOULD be deleted
python schedule_task_cleaner.py --mode prefix

# really delete
python schedule_task_cleaner.py --mode prefix --yes

# delete one specific job's tasks
python schedule_task_cleaner.py --mode job_config --job-config .\job_config.json --yes

# nuke everything (dangerous)
python schedule_task_cleaner.py --mode all --yes
```

---

## 3. `schedule_task_creator.py` — supported schedule modes

| `schedule_mode` | what `schtasks` does | relevant fields |
|---|---|---|
| `once` | run once at `trigger_time` | `trigger_time` |
| `interval` | repeat every `interval_seconds` from `trigger_time` | `trigger_time`, `interval_seconds` (rounded to minutes, min 1) |
| `daily` | run once a day at `trigger_time`'s time-of-day | `trigger_time` |

For an existing task with the same name, the creator calls `schtasks /Delete`
first, so re-running the creator is idempotent.

---

## 4. `schedule_task_cleaner.py` — modes

| mode | what it deletes | extra args |
|---|---|---|
| `all` | every scheduled task on the system | – |
| `prefix` | tasks whose name starts with `SglangScheduledTask_` | – |
| `job_config` | tasks recorded in `tasks.jsonl` against a specific `job_config_path` | `--job-config` |
| `name` | a single named task | `--task-name` |
| `by-script` | tasks in `tasks.jsonl` whose `script_path` matches | `--script-path` |
| `log-only` | every `status=active` task in `tasks.jsonl` (covers renamed tasks) | – |

By default the cleaner is **dry-run**; pass `--yes` to actually delete. On
successful deletion, the log file gets a `status: deleted` record appended.

---

## 5. `schedule_runtime.py` — helpers for job scripts

Importable from the job script via `sys.path`:

```python
sys.path.insert(0, r"d:\personal_code\temp\schedule")
from schedule_runtime import (
    in_window, now, already_done_today, mark_done_today,
    end_task_for_today, delete_task, clear_today_flag,
)
```

Typical use:

```python
# 1) time window guard
if not in_window(dtime(5, 30), dtime(23, 30)):
    return

# 2) "done today" guard
if already_done_today():
    return

# 3) do business...

# 4) if business says "we're done for today":
mark_done_today({"reason": "all branches fetched"})
ok, msg = end_task_for_today(args.task_name)  # schtasks /End -> next day resumes
```

`end_task_for_today` calls `schtasks /End`, which **stops today's remaining
triggers** but does **not** delete the task — the next day the task resumes
on schedule. Use `delete_task` to permanently remove the task.

---

## 6. Notes on the random-looking task name

`task_name` is generated as `SglangScheduledTask_YYYYMMDDhhmmss` (no random
suffix). If you re-create quickly within the same second the name collides,
the creator will first `schtasks /Delete` the old one — so the visible
behavior is "old task replaced with a new one". If you want a true unique
name even within the same second, set a `uuid` field or add a random suffix
in the job config; the cleaner is name-based, so renaming will not break
cleanup (use `--mode log-only` or `--mode by-script`).

---

## 7. `debug/` subdirectory

The `debug/` folder contains standalone example job scripts that exercise
the runtime helpers. See `debug/README.md` for details.
