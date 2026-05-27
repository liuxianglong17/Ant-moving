---
name: "nightly-npu-log-downloader-and-analyzer"
description: "Downloads the latest scheduled NPU nightly test logs and automatically analyzes them to generate test result reports with failed/skipped cases tables. Invoke when user wants to download and analyze NPU nightly test logs in one step, or needs a complete test report from the latest scheduled run."
---

# Nightly NPU Log Downloader and Analyzer

This skill combines log downloading and analysis into a single workflow. It downloads the latest auto-triggered (schedule event) workflow run logs from the `nightly-test-npu.yml` workflow, then automatically analyzes them to generate comprehensive test result reports.

## When to Invoke

- User asks to download and analyze the latest NPU nightly test logs
- User wants a complete test report from today's scheduled NPU workflow run
- User needs to quickly check NPU CI test results without manual steps
- User says something like "下载并分析 NPU 日志" or "get me the NPU test report"

## Workflow Steps

### Phase 1: Download Logs

#### 1.1 Get Latest Scheduled Run

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

#### 1.2 Check Run Date

Compare `run.created_at` with today's date. If the latest scheduled run is not from today, inform the user:
> "The latest scheduled run is from {date}, not today. Do you want to download it anyway?"

#### 1.3 Download Logs

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

#### 1.4 Extract Logs

```powershell
Expand-Archive -Path "nightly-npu-logs-$runId.zip" -DestinationPath "nightly-npu-logs-$runId" -Force
```

### Phase 2: Analyze Logs

#### 2.1 Locate the Analysis Script

Find the log analyzer script:
```
git/log/analyze/analyze-log.py
```

#### 2.2 Run Analysis

Analyze the extracted logs:

```powershell
python "git/log/analyze/analyze-log.py" "nightly-npu-logs-$runId"
```

Or if running from the assistant workspace:
```powershell
cd d:\personal_code\My-agent-assistant
python "git/log/analyze/analyze-log.py" "<path-to-extracted-logs>"
```

#### 2.3 Analysis Output

The analyzer generates two bilingual report files in the log directory:

| 文件名 | 语言 | 说明 |
|--------|------|------|
| `analysis-report.txt` | 英文 | 英文版分析报告 |
| `analysis-report-zh.txt` | 中文 | 中文版分析报告 |

### Phase 3: Report Results

Present a summary to the user including:

1. **Run Information:**
   - Run ID and number
   - Trigger date/time
   - Overall status (success/failure)

2. **Global Statistics:**
   - Total executed cases
   - Passed cases
   - Failed cases
   - Skipped cases (deduplicated)

3. **Failed Cases:**
   - List all failed test cases with pipeline names

4. **Skipped Cases:**
   - List all skipped cases with reasons and pipeline names

5. **Local Paths:**
   - Path to extracted logs
   - Path to analysis reports (`analysis-report.txt` and `analysis-report-zh.txt`)

## Required Parameters

- `workflow_url` - The workflow file URL (e.g., `https://github.com/sgl-project/sglang/actions/workflows/nightly-test-npu.yml`)
- `github_token` - GitHub Personal Access Token with repo scope

## Log Parsing Rules

### Test Summary Matching
```
Test Summary: 45/50 passed
```

### Passed Cases
Lines starting with `/` after `PASSED:` marker:
```
PASSED:
  /path/to/test_case_a.py
  /path/to/test_case_b.py
```

### Failed Cases
Lines starting with `/` after `FAILED:` marker:
```
FAILED:
  /path/to/test_case_c.py
```

### Skipped Cases
```
Skipped 2 test(s):
- /path/to/test_case_f.py (reason: hardware not available)
- /path/to/test_case_g.py (reason: unstable)
```

### Pipeline Name Extraction
Extracted from filenames matching pattern `(nightly|full)-(\d+)`:
- `nightly-8-npu-a3 (0).txt` → `nightly-8-(0)`
- `nightly-16-npu-a3 (1).txt` → `nightly-16-(1)`

## Example Usage

**User Input:**
> "下载并分析 https://github.com/sgl-project/sglang/actions/workflows/nightly-test-npu.yml 今天自动触发的日志"

**Skill Execution:**
1. Parse URL to get owner=`sgl-project`, repo=`sglang`, workflow=`nightly-test-npu.yml`
2. Call API: `GET /repos/sgl-project/sglang/actions/workflows/nightly-test-npu.yml/runs?event=schedule&per_page=5`
3. Find latest scheduled run (e.g., run #998 from 2026-05-25)
4. Check if run date is today
5. If user confirms or date matches, download logs using provided token
6. Extract ZIP archive
7. Run `analyze-log.py` on the extracted directory
8. Read `analysis-report.txt` and `analysis-report-zh.txt`
9. Report summary to user with statistics, failed cases, skipped cases, and file paths

## Notes

- Scheduled runs typically trigger once per day
- If no run exists for today, the latest scheduled run will be used (with user confirmation)
- Logs are retained for approximately 90 days
- The workflow runs on self-hosted NPU runners (linux-aarch64-a3-*)
- Skip cases are globally deduplicated (same case name only kept once)
- Both English and Chinese reports are generated automatically
- Files without test summaries or skip cases are ignored during analysis
