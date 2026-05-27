# GitHub Actions Log Downloader

A PowerShell-based tool to download GitHub Actions workflow run logs by workflow run URL.

## Features

- **Workflow run URL parsing**: Extract owner/repo/run-id from GitHub workflow run URL
- **Auto token loading**: Reads GitHub token from `local_data/github_token.txt` if not provided
- **Auto date detection**: Detects the workflow run date and organizes output by date
- **Large file support**: 300-second timeout + 3 automatic retries
- **Detailed download report**: Generates `download-summary.json`

## Directory Structure

```
git/log/download/
├── download-log.ps1       # Main script
├── README.md              # English documentation
└── README-zh.md           # Chinese documentation
```

## Usage

### Download with auto token

```powershell
powershell -ExecutionPolicy Bypass -File "git/log/download/download-log.ps1" `
  -WorkflowUrl "https://github.com/sgl-project/sglang/actions/runs/26414786878"
```

### Download with explicit token

```powershell
powershell -ExecutionPolicy Bypass -File "git/log/download/download-log.ps1" `
  -WorkflowUrl "https://github.com/sgl-project/sglang/actions/runs/26414786878" `
  -Token "ghp_your_token_here"
```

### Parameters

| Parameter   | Type   | Required | Default | Description                          |
|-------------|--------|----------|---------|--------------------------------------|
| WorkflowUrl | string | Yes      | -       | GitHub workflow run URL              |
| Token       | string | No       | Auto    | GitHub Personal Access Token         |

## Output Directory Structure

```
local_data/logs/
└── {YYYY-MM-DD}/                        # Workflow run date (local time)
    └── {owner}-{repo}-{run_id}/         # Example: sgl-project-sglang-26414786878
        ├── job-name-1.txt
        ├── job-name-2.txt
        └── download-summary.json
```

## Token Setup

Place GitHub Personal Access Token in:
```
local_data/github_token.txt
```

Token requires `repo` scope.

## Example Output

```
=== GitHub Actions Log Downloader ===
Repository: sgl-project/sglang
Run ID: 26414786878

Token loaded from: D:\personal_code\My-agent-assistant\local_data\github_token.txt
Workflow run date (local): 2026-05-26
Output directory: D:\personal_code\My-agent-assistant\local_data\logs\2026-05-26\sgl-project-sglang-26414786878

Fetching jobs for run 26414786878...
Found 9 jobs

Processing job: set-image-config
  Status: completed, Conclusion: success
  OK (0.01 MB)

Processing job: nightly-1-npu-a3 (0)
  Status: completed, Conclusion: failure
  OK (45.23 MB)

========================================
Download complete!
Output directory: D:\personal_code\My-agent-assistant\local_data\logs\2026-05-26\sgl-project-sglang-26414786878
Total jobs: 9, Downloaded: 9, Failed: 0
========================================
```

## Notes

- Token file: `local_data/github_token.txt` (requires `repo` scope)
- Logs are organized by the workflow run's local date
- The script retries up to 3 times on download failure
- Supports large log files (300-second timeout)
