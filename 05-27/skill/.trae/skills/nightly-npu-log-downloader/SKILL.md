---
name: "nightly-npu-log-downloader"
description: "Downloads the latest auto-triggered (schedule event) logs from the nightly-test-npu.yml workflow. Invoke when user wants to download today's or the most recent scheduled NPU nightly test logs."
---

# Nightly NPU Log Downloader

This skill downloads the latest auto-triggered (schedule event) workflow run logs from the `nightly-test-npu.yml` workflow in the `sgl-project/sglang` repository.

## When to Invoke

- User asks to download the latest NPU nightly test logs
- User wants today's automatically triggered NPU workflow logs
- User provides a workflow file URL and wants the most recent scheduled run logs
- User needs to analyze the latest scheduled NPU CI failures

## Workflow Steps

### 1. Get Latest Scheduled Run

Call the GitHub API to list workflow runs, filtering for `event: schedule`:

```
GET https://api.github.com/repos/sgl-project/sglang/actions/workflows/nightly-test-npu.yml/runs?event=schedule&per_page=5
```

Extract the first run (most recent scheduled run):
- `run.id` - Run ID
- `run.run_number` - Run number
- `run.created_at` - Trigger time
- `run.conclusion` - Status (success/failure)
- `run.head_sha` - Commit SHA

### 2. Check Run Date

Compare `run.created_at` with today's date. If the latest scheduled run is not from today, inform the user:
> "The latest scheduled run is from {date}, not today. Do you want to download it anyway?"

### 3. Download Logs

Use the GitHub API to download logs (requires authentication):

**PowerShell:**
```powershell
$headers = @{
    "Accept" = "application/vnd.github+json"
    "Authorization" = "Bearer $token"
    "X-GitHub-Api-Version" = "2022-11-28"
}
Invoke-WebRequest -Uri "https://api.github.com/repos/sgl-project/sglang/actions/runs/$runId/logs" -Headers $headers -OutFile "nightly-npu-logs-$runId.zip"
```

### 4. Extract Logs

```powershell
Expand-Archive -Path "nightly-npu-logs-$runId.zip" -DestinationPath "nightly-npu-logs-$runId" -Force
```

### 5. Analyze and Report

List all job logs and identify failures:
```powershell
Get-ChildItem -Path "nightly-npu-logs-$runId" -Filter "*.txt" | Select-Object Name
```

Search for common error patterns:
- `RuntimeError:`
- `FAILED`
- `Error:`
- `exit code`
- `No backend type associated with device type`

## Required Parameters

- `workflow_url` - The workflow file URL (e.g., `https://github.com/sgl-project/sglang/actions/workflows/nightly-test-npu.yml`)
- `github_token` - GitHub Personal Access Token with repo scope

## Example Usage

**User Input:**
> "下载 https://github.com/sgl-project/sglang/actions/workflows/nightly-test-npu.yml 这个流水线今天自动触发的日志"

**Skill Execution:**
1. Parse URL to get owner=`sgl-project`, repo=`sglang`, workflow=`nightly-test-npu.yml`
2. Call API: `GET /repos/sgl-project/sglang/actions/workflows/nightly-test-npu.yml/runs?event=schedule&per_page=5`
3. Find latest scheduled run (e.g., run #998 from 2026-05-25)
4. Check if run date is today
5. If user confirms or date matches, download logs using provided token
6. Extract ZIP and analyze
7. Report: run number, date, status, failed jobs, and error summary

## Output Format

Report to user with:
- Run ID and number
- Trigger date/time
- Overall status
- List of jobs with their status
- Key errors found
- Local path to extracted logs

## Notes

- Scheduled runs typically trigger once per day
- If no run exists for today, the latest scheduled run will be used
- Logs are retained for approximately 90 days
- The workflow runs on self-hosted NPU runners (linux-aarch64-a3-*)
