# nightly-log-reporter

A turnkey tool for **downloading + analyzing** GitHub Actions workflow logs
(used today for `sgl-project/sglang` nightly and `sgl-project/sgl-kernel-npu` daily builds,
but works for any GitHub repo).

Supports both **single-target** mode (one workflow) and **multi-target** mode
(multiple workflows in the same or different repos, run sequentially).

---

## 1. Quick start

### 1.1 One-line entry (recommended)

```bat
:: Windows cmd / double-click
run_all.bat
```

`run_all.bat` internally calls PowerShell with `-ExecutionPolicy Bypass`,
which is required because Windows 5.1 PowerShell blocks `.ps1` execution by default.

### 1.2 Manual PowerShell

```powershell
# today
.\run_all.ps1

# specific date (writes to outputs\06-03\)
.\run_all.ps1 -Date 06-03

# skip parts of the pipeline
.\run_all.ps1 -SkipFind
.\run_all.ps1 -SkipFind -SkipDownload
.\run_all.ps1 -SkipAnalyze
.\run_all.ps1 -SkipSummary
```

### 1.3 Multi-target mode

```powershell
# run all targets in targets.config.json
.\run_all.ps1 -TargetsConfig .\config\targets.config.json

# run only one named target
.\run_all.ps1 -TargetsConfig .\config\targets.config.json -Target sglang-npu
```

`run_all.ps1` runs **find → download → analyze → classify → summary** in order
for each target; if any step for a target fails, it aborts immediately
(downstream analysis depends on the full pipeline).

---

## 2. Outputs

### 2.1 Single-target layout

```
outputs\06-04\
├── workflow-info.json
├── download-summary.json
├── summary.txt                  # ← produced by build_summary.py
└── <owner>-<repo>-<run_id>\
    ├── *.txt                    # raw job logs (one per job)
    ├── analysis-report.txt      # English test/jobs report
    ├── analysis-report-zh.txt   # Chinese test/jobs report
    ├── analysis-brief.json      # machine-readable brief
    ├── error-classification-report.txt
    └── error-classification-report-zh.txt
```

### 2.2 Multi-target layout

```
outputs\06-04\
├── summary.txt                  # combined brief for all targets
├── sglang-npu\
│   ├── workflow-info.json
│   ├── download-summary.json
│   └── <owner>-<repo>-<run_id>\... (same as above)
└── sgl-kernel-npu\
    └── ... (same as above)
```

### 2.3 `summary.txt` example

```
Nightly流水线：
kernel：通过率100.0% (执行job 8, 通过job 8, 失败job 0)
sglang：通过率87.2% (执行用例86, 通过用例75, 失败用例11)
```

Each target is rendered according to its analyzer mode (case vs job).
The displayed label comes from `targets.config.json → targets[i].label`
(falls back to `name`).

---

## 3. Multi-target config

`config\targets.config.json`:

```json
{
  "targets": [
    {
      "name": "sglang-npu",
      "label": "sglang",
      "finder": {
        "workflow_url": "https://github.com/sgl-project/sglang/actions/workflows/nightly-test-npu.yml",
        "branch": "main",
        "event": "schedule",
        "date": "",
        "start_date": "",
        "end_date": "",
        "max_pages": 5
      },
      "downloader": {
        "repo": "sgl-project/sglang",
        "timeout_sec": 300,
        "max_retries": 3
      },
      "analyzer": { "mode": "case" }
    },
    {
      "name": "sgl-kernel-npu",
      "label": "kernel",
      "finder": {
        "workflow_url": "https://github.com/sgl-project/sgl-kernel-npu/actions/workflows/daily-build-test.yml",
        "branch": "main",
        "event": "schedule",
        "max_pages": 5
      },
      "downloader": { "repo": "sgl-project/sgl-kernel-npu" },
      "analyzer": { "mode": "job" }
    }
  ]
}
```

| field                  | meaning                                                         |
|------------------------|-----------------------------------------------------------------|
| `name`                 | unique key; also the `outputs\MM-DD\<name>\` directory          |
| `label`                | label used in the combined `summary.txt` (defaults to `name`)   |
| `finder.*`             | same fields as `finder.config.json`                             |
| `downloader.*`         | same fields as `downloader.config.json`                         |
| `analyzer.mode`        | `case` (default; scan `.txt` for test cases) or `job` (API call)|

---

## 4. Repository layout

```
nightly-log-reporter\
├── run_all.bat / run_all.ps1        # entry points
├── config\                          # edit here to change behavior
│   ├── finder.config.json
│   ├── downloader.config.json
│   ├── targets.config.json
│   └── analyzer.config.json
├── scripts\
│   ├── find_workflow\               # ① find workflow runs
│   │   ├── find-workflow.ps1
│   │   └── utils\time-utils.ps1
│   ├── download_log\                # ② download run logs
│   │   └── download-log.ps1
│   ├── analyze\                     # ③ analyze + classify
│   │   ├── analyze-log.py
│   │   └── classify-errors.py
│   └── summary\                     # ④ combined brief
│       └── build_summary.py
├── local_data\
│   └── github_token.txt             # ← REQUIRED, PAT with `repo` + `actions:read`
├── outputs\MM-DD\                   # all per-day results land here
└── logs\                            # run logs (debug)
```

Each `scripts\<step>\` has its own README; see those for per-step details.

---

## 5. First-time setup

1. Create a GitHub Personal Access Token (PAT) with `repo` and `actions:read` scope.
2. Save it to `local_data\github_token.txt` (no trailing newline is fine).

That's it — you can run `run_all.bat` after that.

---

## 6. Adapting to other repos

- **Single-target mode**: edit `config\finder.config.json` (`workflow_url`) and
  `config\downloader.config.json` (`repo`).
- **Multi-target mode**: add/remove entries in `config\targets.config.json`.
- **Different analyzer granularity**: set `analyzer.mode = job` to count
  pass/fail by GitHub Jobs (no log parsing); or `case` to scan the
  `Test Summary: N/M passed` blocks in the log.

---

## 7. Execution policy note

`run_all.ps1` is blocked by Windows PowerShell's default `RemoteSigned` policy
even for the current user. Use one of:

- `run_all.bat` (easiest, calls PowerShell with `-ExecutionPolicy Bypass`)
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\run_all.ps1`
- Set the policy once: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`
