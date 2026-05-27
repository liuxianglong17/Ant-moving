---
name: "git-log-download"
description: "Downloads GitHub Actions workflow run logs using GitHub API. Invoke when user wants to download workflow logs, analyze CI failures, or retrieve GitHub Actions run details."
---

# GitHub Actions Log Downloader

This skill downloads and extracts GitHub Actions workflow run logs for analysis.

## When to Invoke

- User asks to download GitHub Actions workflow logs
- User provides a GitHub Actions run URL and wants the logs
- User needs to analyze CI/CD failures from GitHub Actions
- User wants to inspect workflow execution details

## Prerequisites

- GitHub Personal Access Token (PAT) with `repo` scope (for private repos) or public access
- The workflow run ID or URL

## Steps

### 1. Get Run Information

If user provides a URL like `https://github.com/owner/repo/actions/runs/12345`, extract:
- Owner: `owner`
- Repo: `repo`
- Run ID: `12345`

### 2. Download Logs

Use GitHub API to download logs as ZIP:

**PowerShell:**
```powershell
Invoke-WebRequest -Uri "https://api.github.com/repos/{owner}/{repo}/actions/runs/{run_id}/logs" `
  -Headers @{
    "Accept" = "application/vnd.github+json"
    "Authorization" = "Bearer {token}"
    "X-GitHub-Api-Version" = "2022-11-28"
  } `
  -OutFile "logs.zip"
```

**Bash:**
```bash
curl -L \
  -H "Accept: application/vnd.github+json" \
  -H "Authorization: Bearer {token}" \
  -H "X-GitHub-Api-Version: 2022-11-28" \
  https://api.github.com/repos/{owner}/{repo}/actions/runs/{run_id}/logs \
  -o logs.zip
```

### 3. Extract and Analyze

Extract the ZIP file:
```powershell
Expand-Archive -Path "logs.zip" -DestinationPath "workflow-logs" -Force
```

The extracted structure:
```
workflow-logs/
├── {job-name}/
│   └── system.txt          # Job system info
├── 0_{job-name}.txt        # Main job log
├── 1_{job-name}.txt        # Another job log
└── ...
```

### 4. Analyze Logs

Key patterns to search for:
- `Error:` or `error:` - General errors
- `FAIL` or `FAILED` - Test failures
- `RuntimeError:` - Runtime exceptions
- `exit code` - Process exit codes
- `No backend type associated with device type` - NPU/device errors

Use grep or Select-String to find errors:
```powershell
Select-String -Path "workflow-logs\*.txt" -Pattern "Error:|FAILED|RuntimeError"
```

## Example Workflow

1. User provides: `https://github.com/sgl-project/sglang/actions/runs/26414786878`
2. Extract info: owner=`sgl-project`, repo=`sglang`, run_id=`26414786878`
3. Ask user for GitHub token if not provided
4. Download logs using API
5. Extract ZIP archive
6. Analyze job statuses and errors
7. Report findings with file references

## Notes

- GitHub API requires authentication for log downloads
- Logs are retained based on repository settings (usually 90 days)
- Large logs may take time to download
- The ZIP contains text files for each job step
