---
name: "github-workflow-link-finder"
description: "Query GitHub Actions workflow run links with branch/event/date filtering. Invoke when user asks to find workflow links, filter workflow runs by branch/event/date, or get scheduled/nightly workflow URLs."
---

# GitHub Workflow Link Finder

Query GitHub Actions workflow run links with filtering support (branch, event type, date). Automatically handles local time to UTC conversion for GitHub API.

## When to Invoke

- User wants to find workflow run links for a specific date
- User needs to filter workflow runs by branch, event, or date range
- User asks for scheduled/nightly workflow URLs
- User provides a workflow URL like `https://github.com/owner/repo/actions/workflows/xxx.yml`

## Script Location

```
git/workflow/find_workflow/
├── find-workflow.ps1      # Main script
├── utils/
│   └── time-utils.ps1     # Time conversion utilities
└── README.md
```

## Key Concepts

### Local Time Priority

All date filtering uses **local time**. For example, a workflow triggered at local time 2026-05-26 02:37:52 (UTC+8) has UTC time 2026-05-25T18:37:52Z, but it belongs to **5/26**.

### UTC Conversion Logic

```
Local date "today" = 2026-05-26 00:00:00 ~ 2026-05-26 23:59:59
    ↓ Convert to UTC (UTC+8 timezone)
UTC range = 2026-05-25T16:00:00Z ~ 2026-05-26T16:00:00Z
```

### Scheduled Workflow Identification

A scheduled (nightly) workflow satisfies:
```
event == "schedule" AND head_branch == "main"
```

## Usage Examples

### Find today's scheduled workflow

```powershell
powershell -ExecutionPolicy Bypass -File "git/workflow/find_workflow/find-workflow.ps1" `
  -WorkflowUrl "https://github.com/sgl-project/sglang/actions/workflows/nightly-test-npu.yml" `
  -Branch "main" `
  -Event "schedule" `
  -Date "2026-05-26"
```

### Find workflows in a date range

```powershell
powershell -ExecutionPolicy Bypass -File "git/workflow/find_workflow/find-workflow.ps1" `
  -WorkflowUrl "https://github.com/sgl-project/sglang/actions/workflows/nightly-test-npu.yml" `
  -Branch "main" `
  -Event "schedule" `
  -StartDate "2026-05-20" `
  -EndDate "2026-05-26"
```

## Parameters

| Parameter   | Required | Description                          |
|-------------|----------|--------------------------------------|
| WorkflowUrl | Yes      | GitHub workflow URL                  |
| Branch      | No       | Filter by branch (e.g., `main`)      |
| Event       | No       | Filter by event (e.g., `schedule`)   |
| Date        | No*      | Single date (format: `yyyy-MM-dd`)   |
| StartDate   | No*      | Range start (format: `yyyy-MM-dd`)   |
| EndDate     | No*      | Range end (format: `yyyy-MM-dd`)     |
| MaxPages    | No       | Max API pages (default: 10)          |

\* Either `Date` or both `StartDate` and `EndDate` must be provided.

## Token Setup

Place GitHub Personal Access Token in:
```
local_data/github_token.txt
```

Token requires `repo` scope.

## Output Format

The script prints matching workflow details including:
- URL (direct link to the workflow run)
- ID
- Branch
- Event
- Status / Conclusion
- Local Time
- UTC Time
