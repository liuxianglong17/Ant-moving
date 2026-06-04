# scripts/download_log

Step ② of the `nightl-log-reporter` pipeline. Reads `workflow-info.json`
produced by `find_workflow`, then for each matched run downloads every
job's plain-text log via the GitHub Jobs API. Writes
`download-summary.json` so downstream analysis can locate the per-run
directories.

---

## Files

| file | role |
|---|---|
| `download-log.ps1` | Main script. Pulls all jobs for each run (`/repos/{owner}/{repo}/actions/runs/{id}/jobs`), then downloads `/actions/jobs/{job_id}/logs` for each job into `<owner>-<repo>-<run_id>\` directories. |

---

## Usage

```powershell
# defaults: workflow-info.json + outputs\MM-DD\ in repo root
.\scripts\download_log\download-log.ps1

# explicit (multi-target mode used by run_all.ps1)
.\scripts\download_log\download-log.ps1 `
    -ConfigPath .\config\downloader.config.json `
    -InfoPath   .\outputs\06-04\sglang-npu\workflow-info.json `
    -OutDir     .\outputs\06-04\sglang-npu `
    -Repo       "sgl-project/sglang"
```

`run_all.ps1` calls this for each target after `find-workflow.ps1`
finishes.

---

## Config (`config\downloader.config.json`)

```json
{
  "repo":        "sgl-project/sglang",   // owner/repo; overridden by -Repo in multi-target mode
  "timeout_sec": 300,                    // per-request timeout
  "max_retries": 3                       // retries on failure (5s sleep between)
}
```

`run_all.ps1` generates per-target downloader configs in
`logs\.tmp\<timestamp>\downloader.<target>.json` from `targets.config.json`
when in multi-target mode.

---

## Output layout

For each run in `workflow-info.json`, the script creates:

```
<OutDir>\
├── download-summary.json
└── <owner>-<repo>-<run_id>\
    ├── <job1>.txt       (raw job log)
    ├── <job2>.txt
    └── ...
```

`download-summary.json` is the canonical record:

```json
{
  "repo": "sgl-project/sglang",
  "downloaded_at": "2026-06-04 14:30:01",
  "total_runs": 1,
  "total_downloaded": 7,
  "total_failed": 0,
  "runs": [
    {
      "run_id": 26907746244,
      "run_url": "https://github.com/sgl-project/sglang/actions/runs/26907746244",
      "branch": "main",
      "event":  "schedule",
      "local_created": "2026-06-04 20:00:00",
      "total_jobs": 7,
      "downloaded": 7,
      "failed":     0,
      "output_dir": "...\\outputs\\06-04\\sglang-npu\\sgl-project-sglang-26907746244"
    }
  ]
}
```

The downloader also **filters runs**: if `workflow-info.json` has zero
runs, the script exits cleanly (and `download-summary.json` is not
written).

---

## GitHub token

Same lookup as the finder:

1. `<repo_root>\local_data\github_token.txt`
2. `D:\personal_code\My-agent-assistant\local_data\github_token.txt`

---

## Error handling

On failure the script writes the error to
`<repo_root>\logs\downloader-last-error.txt`. `run_all.ps1` aborts the
whole run if that file is present after the call. Per-job failures are
retried up to `max_retries` and counted in `download-summary.json`; the
script itself only aborts on infrastructure errors (missing info file,
token, etc.).
