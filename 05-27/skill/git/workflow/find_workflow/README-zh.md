# GitHub Actions 工作流链接查询工具

基于 PowerShell 实现的 GitHub Actions 工作流运行链接查询工具，支持按分支、触发事件、日期筛选，并自动处理本地时间与 UTC 的转换。

## 功能特性

- **工作流 URL 解析**：从 GitHub 工作流链接中提取 owner/repo/workflow-id
- **分支筛选**：按 `head_branch` 筛选
- **事件筛选**：按触发事件筛选（`schedule`、`push`、`pull_request` 等）
- **日期筛选**：按本地日期筛选（自动转换为 UTC 调用 GitHub API）
- **日期范围筛选**：支持起始/结束日期范围查询
- **自动读取 Token**：从 `local_data/github_token.txt` 自动读取

## 目录结构

```
find_workflow/
├── find-workflow.ps1      # 主脚本
├── utils/
│   └── time-utils.ps1     # 时间转换工具
├── README.md              # 英文文档
└── README-zh.md           # 中文文档
```

## 使用方法

### 按单日期查询

```powershell
powershell -ExecutionPolicy Bypass -File "git/workflow/find_workflow/find-workflow.ps1" `
  -WorkflowUrl "https://github.com/sgl-project/sglang/actions/workflows/nightly-test-npu.yml" `
  -Branch "main" `
  -Event "schedule" `
  -Date "2026-05-26"
```

### 按日期范围查询

```powershell
powershell -ExecutionPolicy Bypass -File "git/workflow/find_workflow/find-workflow.ps1" `
  -WorkflowUrl "https://github.com/sgl-project/sglang/actions/workflows/nightly-test-npu.yml" `
  -Branch "main" `
  -Event "schedule" `
  -StartDate "2026-05-20" `
  -EndDate "2026-05-26"
```

### 参数说明

| 参数        | 类型   | 必填 | 默认值 | 说明                                 |
|-------------|--------|------|--------|--------------------------------------|
| WorkflowUrl | string | 是   | -      | GitHub 工作流链接                    |
| Branch      | string | 否   | -      | 按分支筛选（如 `main`）              |
| Event       | string | 否   | -      | 按事件筛选（如 `schedule`）          |
| Date        | string | 否*  | -      | 单日期（格式：`yyyy-MM-dd`）         |
| StartDate   | string | 否*  | -      | 范围起始日期（格式：`yyyy-MM-dd`）   |
| EndDate     | string | 否*  | -      | 范围结束日期（格式：`yyyy-MM-dd`）   |
| MaxPages    | int    | 否   | 10     | 最大获取页数（每页 100 条）          |

\* `Date` 与 `StartDate`/`EndDate` 两组参数必须提供其一。

## 时间转换逻辑

GitHub API 返回的 `created_at` 是 UTC 时间。本工具以**本地时间**为准进行筛选：

```
用户输入本地日期：2026-05-26
本地时间范围：2026-05-26 00:00:00 ~ 2026-05-26 23:59:59
转换为 UTC（UTC+8 时区）：2026-05-25T16:00:00Z ~ 2026-05-26T16:00:00Z
```

脚本会将本地日期范围转换为 UTC 后再与 API 返回结果进行比较。

## 识别定时触发（Nightly）工作流

定时触发的 nightly 工作流通常需同时满足：

```
event == "schedule" AND head_branch == "main"
```

## 输出示例

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

## 注意事项

- Token 文件：`local_data/github_token.txt`（需要 `repo` 权限）
- 脚本最多从 GitHub API 获取 `MaxPages * 100` 条工作流记录
- 若未找到结果，请检查日期和筛选条件是否正确
