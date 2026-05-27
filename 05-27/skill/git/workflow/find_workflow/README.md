# GitHub Actions Workflow Link Finder

A PowerShell-based tool to query GitHub Actions workflow run links with filtering support (branch, event type, date). Handles local time to UTC conversion automatically.

## Features

- **Workflow URL parsing**: Extract owner/repo/workflow-id from GitHub workflow URL
- **Branch filtering**: Filter by `head_branch`
- **Event filtering**: Filter by trigger event (`schedule`, `push`, `pull_request`, etc.)
- **Date filtering**: Filter by local date (automatically converted to UTC for GitHub API)
- **Date range filtering**: Support start/end date range
- **Auto token loading**: Reads GitHub token from `local_data/github_token.txt`

## Directory Structure

```
find_workflow/
├── find-workflow.ps1      # Main script
├── utils/
│   └── time-utils.ps1     # Time conversion utilities
├── README.md              # English documentation
└── README-zh.md           # Chinese documentation
```

## Usage

### Query by single date

```powershell
powershell -ExecutionPolicy Bypass -File "git/workflow/find_workflow/find-workflow.ps1" `
  -WorkflowUrl "https://github.com/sgl-project/sglang/actions/workflows/nightly-test-npu.yml" `
  -Branch "main" `
  -Event "schedule" `
  -Date "2026-05-26"
```

### Query by date range

```powershell
powershell -ExecutionPolicy Bypass -File "git/workflow/find_workflow/find-workflow.ps1" `
  -WorkflowUrl "https://github.com/sgl-project/sglang/actions/workflows/nightly-test-npu.yml" `
  -Branch "main" `
  -Event "schedule" `
  -StartDate "2026-05-20" `
  -EndDate "2026-05-26"
```

### Parameters

| Parameter   | Type   | Required | Default | Description                          |
|-------------|--------|----------|---------|--------------------------------------|
| WorkflowUrl | string | Yes      | -       | GitHub workflow URL                  |
| Branch      | string | No       | -       | Filter by branch (e.g., `main`)      |
| Event       | string | No       | -       | Filter by event (e.g., `schedule`)   |
| Date        | string | No*      | -       | Single date (format: `yyyy-MM-dd`)   |
| StartDate   | string | No*      | -       | Range start (format: `yyyy-MM-dd`)   |
| EndDate     | string | No*      | -       | Range end (format: `yyyy-MM-dd`)     |
| MaxPages    | int    | No       | 10      | Max API pages to fetch (100 per page)|

\* Either `Date` or both `StartDate` and `EndDate` must be provided.

## Time Conversion Logic

GitHub API returns `created_at` in UTC. This tool filters by **local time**:

```
User inputs local date: 2026-05-26
Local time range: 2026-05-26 00:00:00 ~ 2026-05-26 23:59:59
UTC time range (UTC+8): 2026-05-25T16:00:00Z ~ 2026-05-26T16:00:00Z
```

The script converts the local date range to UTC before comparing with API results.

## Identifying Scheduled (Nightly) Workflows

A scheduled nightly workflow typically satisfies:

```
event == "schedule" AND head_branch == "main"
```

## Example Output

```
=== Workflow Query ===
Repository: sgl-project/sglang
Workflow: nightly-test-npu.yml

Filters: Branch=main, Event=schedule, Date=2026-05-26
UTC Range: 2026-05-25T16:00:00Z ~ 2026-05-26T16:00:00Z

=== Query Results ===
Found 1 matching workflow(s)

URL: https://github.com/sgl-project/sglang/actions/runs/26414786878
ID: 26414786878
Branch: main
Event: schedule
Status: completed
Conclusion: success
Local Time: 2026-05-26 02:37:52
UTC Time: 2026-05-25T18:37:52Z

=== Query End ===
```

## Notes

- Token file: `local_data/github_token.txt` (requires `repo` scope)
- The script fetches up to `MaxPages * 100` workflow runs from GitHub API
- If no results are found, verify the date and filter criteria
