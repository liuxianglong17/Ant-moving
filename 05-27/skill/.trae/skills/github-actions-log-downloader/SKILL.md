---
name: "github-actions-log-downloader"
description: "Downloads GitHub Actions workflow run logs. Supports auto-reading token from local_data, large file download with retry, and automatic directory organization by date/pipeline name."
---

# GitHub Actions Log Downloader

基于 PowerShell 实现的 GitHub Actions 日志下载工具，支持自动读取 token 和大文件重试下载。

## 功能特性

- ✅ **自动读取 token**：从 `local_data/github_token.txt` 自动读取，无需每次输入
- ✅ **大文件支持**：300 秒超时 + 3 次自动重试，支持 200MB+ 日志文件
- ✅ **智能目录组织**：按日期/流水线名自动创建目录结构
- ✅ **日志文件直接存储**：每个 job 的日志直接以 `.txt` 文件保存
- ✅ **日期范围筛选**：使用 GitHub API 的 `created` 参数高效筛选指定日期范围
- ✅ **详细下载报告**：生成 `download-summary.json` 汇总信息

## 目录结构

```
My-agent-assistant/
├── local_data/                    # 🔒 本地数据（不上库）
│   └── github_token.txt           # GitHub Personal Access Token
├── git-log-download/              # 日志下载工具主目录
│   ├── README.md                  # 使用说明
│   └── git-log-downloader.ps1     # ✅ PowerShell 下载核心脚本
└── git-workflow-statistics/       # 工作流统计工具
    └── download-workflow-data.ps1 # ✅ 工作流数据批量下载脚本
```

## 快速开始

### 1. 配置 Token

将 GitHub Personal Access Token 放入以下文件：
```
local_data/github_token.txt
```

Token 要求：需要 `repo` 权限

### 2. 下载单个 Workflow Run 日志

```powershell
cd D:\personal_code\My-agent-assistant

powershell -ExecutionPolicy Bypass -File "git-log-download/git-log-downloader.ps1" `
  -Repo "sgl-project/sglang" `
  -RunId "26183215652"
```

**默认输出路径**：`local_data/logs/YYYY-MM-DD/owner-repo-run_id/`

### 3. 批量下载指定日期范围的 Workflow 数据

```powershell
powershell -ExecutionPolicy Bypass -File "git-workflow-statistics/download-workflow-data.ps1" `
  -StartDate "2026-05-18" `
  -EndDate "2026-05-25" `
  -WorkflowId "pr-test-npu.yml"
```

## 日期范围筛选说明

### 本地时间优先原则

所有日期判断均**以本地时间为准**。例如本地时间 2026-05-26 02:37:52（UTC+8）对应的 UTC 时间是 2026-05-25T18:37:52Z，但该工作流应判定为 **5/26 日** 的任务。

### UTC 时间转换逻辑

```
本地时间 "今天" = 2026-05-26 00:00:00 ~ 2026-05-26 23:59:59
    ↓ 转换为 UTC（UTC+8 时区）
UTC 时间范围 = 2026-05-25T16:00:00Z ~ 2026-05-26T16:00:00Z
```

### GitHub API created 参数

使用 `created` 参数高效筛选工作流运行记录：

```
# 获取 2026-05-18 至 2026-05-25 之间的所有运行
created:>=2026-05-18 created:<2026-05-26

# 格式说明
created:>=YYYY-MM-DD    # 大于等于指定日期
created:<YYYY-MM-DD     # 小于指定日期（不包含当天）
```

### API URL 示例

```
https://api.github.com/repos/sgl-project/sglang/actions/workflows/pr-test-npu.yml/runs
  ?per_page=100
  &created:>=2026-05-18
  &created:<2026-05-26
```

### 自动触发任务识别规则

自动触发（Scheduled）的 nightly 任务需同时满足：

```
event == "schedule" AND head_branch == "main"
```

### 历史触发时间规律

根据历史数据，nightly 任务通常在**本地时间凌晨 02:26 ~ 02:37** 之间触发。

## 日志组织规则

### 目录命名规则

```
local_data/logs/
└── {日期}/                              # 格式：YYYY-MM-DD
    └── {owner}-{repo}-{run_id}/         # 格式：sgl-project-sglang-26183215652
```

### 文件命名规则

- 每个 job 的日志直接存储为 `.txt` 文件
- 文件名 = job 名 + `.txt`
- 示例：
  - `set-image-config.txt`
  - `nightly-1-npu-a3 (0).txt`
  - `download-summary.json`

## 参数说明

### git-log-downloader.ps1

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `Repo` | string | 是 | - | 仓库名，格式：`owner/repo` |
| `RunId` | string | 是 | - | Workflow run ID |
| `Token` | string | 否 | 自动读取 | GitHub Personal Access Token |
| `OutputDir` | string | 否 | `local_data/logs/日期/owner-repo-run_id` | 输出目录 |
| `TimeoutSec` | int | 否 | 300 | 单个日志下载超时时间（秒） |
| `MaxRetries` | int | 否 | 3 | 下载失败时最大重试次数 |

### download-workflow-data.ps1

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `Repo` | string | 否 | `sgl-project/sglang` | 仓库名 |
| `WorkflowId` | string | 否 | `pr-test-npu.yml` | 工作流 ID 或文件名 |
| `StartDate` | string | 否 | 当天 | 开始日期（格式：`YYYY-MM-DD`） |
| `EndDate` | string | 否 | 当天 | 结束日期（格式：`YYYY-MM-DD`） |
| `OutputDir` | string | 否 | `local_data/logs` | 输出目录 |

## 使用示例

### 基本用法（下载单个 Run 日志）

```powershell
powershell -ExecutionPolicy Bypass -File "git-log-download/git-log-downloader.ps1" `
  -Repo "sgl-project/sglang" `
  -RunId "26183215652"
```

### 批量下载指定日期范围的工作流数据

```powershell
powershell -ExecutionPolicy Bypass -File "git-workflow-statistics/download-workflow-data.ps1" `
  -StartDate "2026-05-18" `
  -EndDate "2026-05-25" `
  -WorkflowId "pr-test-npu.yml"
```

### 手动指定 token（临时使用）

```powershell
powershell -ExecutionPolicy Bypass -File "git-log-download/git-log-downloader.ps1" `
  -Token "ghp_your_token_here" `
  -Repo "sgl-project/sglang" `
  -RunId "26183215652"
```

### 增加超时和重试次数

```powershell
powershell -ExecutionPolicy Bypass -File "git-log-download/git-log-downloader.ps1" `
  -Repo "sgl-project/sglang" `
  -RunId "26183215652" `
  -TimeoutSec 600 `
  -MaxRetries 5
```

## 输出示例

```
GitHub Actions Workflow Data Downloader
Using created parameter for efficient date filtering
GitHub Token loaded
Parameters:
  Repo: sgl-project/sglang
  Workflow: pr-test-npu.yml
  Date Range: 2026-05-18 to 2026-05-25
Fetching page 1...
URL: https://api.github.com/repos/sgl-project/sglang/actions/workflows/pr-test-npu.yml/runs?per_page=100&page=1&created=>=2026-05-18&created=<2026-05-26
Found 100 runs on page 1
Fetch complete! Total records: 1000
Merged data saved to: D:\personal_code\My-agent-assistant\local_data\logs\merged\workflow-data_2026-05-18_to_2026-05-25.csv
2026-05-18 : no data
2026-05-19 : no data
2026-05-20 : no data
2026-05-21 : no data
2026-05-22 : 91 records
2026-05-23 : 267 records
2026-05-24 : 190 records
2026-05-25 : 452 records
Download completed successfully
```

## 注意事项

1. **Token 安全**：`local_data/` 目录已配置为不上库，请确保 `.gitignore` 正确配置
2. **网络要求**：需要能访问 GitHub API (api.github.com)
3. **大文件下载**：建议在网络稳定时下载 100MB 以上的日志文件
4. **重试机制**：下载失败会自动重试 3 次，每次间隔 5 秒
5. **日期范围**：使用 `created` 参数比逐页扫描更高效，尤其是需要获取较早数据时

## 故障排除

### 常见问题

**Q: 未找到 token 文件**
```
GitHub token file not found
```
**A:** 将 GitHub Token 放入 `local_data/github_token.txt` 文件中

**Q: 下载超时**
```
Timeout (300s)
```
**A:** 网络较慢或日志文件太大，脚本会自动重试

**Q: Token 无效**
```
401 Unauthorized
```
**A:** 检查 Token 是否正确，是否具有 `repo` 权限

**Q: 远程主机强制关闭连接**
```
无法从传输连接中读取数据: 远程主机强迫关闭了一个现有的连接
```
**A:** 网络不稳定，脚本会自动重试，建议稍后重试或使用更稳定的网络

**Q: 某些日期没有数据**
```
2026-05-18 : no data
```
**A:** 这表示该日期 GitHub 上确实没有该工作流的运行记录，属于正常情况
