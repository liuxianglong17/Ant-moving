# scripts/find_workflow

Step ① of the `nightl-log-reporter` pipeline. Reads its config, calls the
GitHub REST API for workflow runs, and writes a machine-readable
`workflow-info.json` for the downloader to consume.

---

## Files

| file | role |
|---|---|
| `find-workflow.ps1` | Main script. Reads `config\finder.config.json`, calls `/repos/{owner}/{repo}/actions/workflows/{id}/runs`, filters by branch/event/date, writes `<out_dir>\workflow-info.json`. |
| `utils\time-utils.ps1` | Helpers for converting local dates to UTC ranges (`Get-DateRangeUtc`, `Get-DateRangeUtcFromStartEnd`). |

---

## Usage

```powershell
# from the repo root, using the default config (today, single-target mode)
.\scripts\find_workflow\find-workflow.ps1

# with explicit parameters
.\scripts\find_workflow\find-workflow.ps1 `
    -ConfigPath   .\config\finder.config.json `
    -OutDir       .\outputs\06-04 `
    -Date         "2026-06-03" `
    -WorkflowUrl  "https://github.com/sgl-project/sglang/actions/workflows/nightly-test-npu.yml"
```

`run_all.ps1` calls this script with appropriate arguments; you usually do
not need to invoke it directly.

---

## Config (`config\finder.config.json`)

```json
{
  "workflow_url": "https://github.com/sgl-project/sglang/actions/workflows/nightly-test-npu.yml",
  "branch": "main",
  "event":  "schedule",
  "date":   "",            // yyyy-MM-dd; empty = today
  "start_date": "",        // optional, used if both start_date and end_date are set
  "end_date":   "",
  "max_pages":  5          // GitHub API page cap; 5*100 = 500 runs
}
```

| field | meaning |
|---|---|
| `workflow_url` | The Actions workflow URL (used to derive owner/repo/workflow file name). |
| `branch`       | Filter to runs on this branch (empty = no filter). |
| `event`        | Filter to runs of this event (`schedule`, `push`, `workflow_dispatch`, ...). |
| `date`         | `yyyy-MM-dd`. Empty defaults to today. |
| `start_date` / `end_date` | Range mode; takes precedence over `date` if all three are set. |
| `max_pages`    | Max GitHub API pages to walk (100 results per page). |

---

## Output

`<out_dir>\workflow-info.json`:

```json
{
  "generated_at": "2026-06-04 14:29:03",
  "config":  { "workflow_url": "...", "branch": "main", "event": "schedule", "date": "2026-06-04" },
  "runs": [
    {
      "id": 26907746244,
      "url": "https://github.com/sgl-project/sglang/actions/runs/26907746244",
      "repo": "sgl-project/sglang",
      "owner": "sgl-project",
      "repo_name": "sglang",
      "workflow_id": "nightly-test-npu.yml",
      "branch": "main",
      "event": "schedule",
      "status": "completed",
      "conclusion": "success",
      "utc_created": "2026-06-04T12:00:00Z",
      "local_created": "2026-06-04 20:00:00",
      "local_date": "2026-06-04"
    }
  ]
}
```

The output directory defaults to `<repo_root>\outputs\<MM-DD>\` (where
`<MM-DD>` is computed from the active `date` / range), but `run_all.ps1`
explicitly passes `-OutDir` in multi-target mode so each target gets its
own subdirectory.

---

## GitHub token

The script reads the PAT from the first existing file in this list:

1. `<repo_root>\local_data\github_token.txt`
2. `D:\personal_code\My-agent-assistant\local_data\github_token.txt`

The PAT needs `repo` and `actions:read` scopes (and `actions:read` for
private repos if applicable).

---

## Error handling

On failure the script writes the error message to
`<repo_root>\logs\finder-last-error.txt`. `run_all.ps1` checks for this
file after the call and aborts the whole run if it exists.
