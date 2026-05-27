# GitHub Actions 日志下载工具

基于 PowerShell 实现的 GitHub Actions 工作流运行日志下载工具，通过工作流运行链接即可下载全部日志。

## 功能特性

- **工作流运行 URL 解析**：从 GitHub 工作流运行链接中提取 owner/repo/run-id
- **自动读取 Token**：未提供 Token 时自动从 `local_data/github_token.txt` 读取
- **自动日期检测**：根据工作流运行时间自动按日期组织输出目录
- **大文件支持**：300 秒超时 + 3 次自动重试
- **详细下载报告**：生成 `download-summary.json` 汇总信息

## 目录结构

```
git/log/download/
├── download-log.ps1       # 主脚本
├── README.md              # 英文文档
└── README-zh.md           # 中文文档
```

## 使用方法

### 自动读取 Token 下载

```powershell
powershell -ExecutionPolicy Bypass -File "git/log/download/download-log.ps1" `
  -WorkflowUrl "https://github.com/sgl-project/sglang/actions/runs/26414786878"
```

### 手动指定 Token 下载

```powershell
powershell -ExecutionPolicy Bypass -File "git/log/download/download-log.ps1" `
  -WorkflowUrl "https://github.com/sgl-project/sglang/actions/runs/26414786878" `
  -Token "ghp_your_token_here"
```

### 参数说明

| 参数        | 类型   | 必填 | 默认值 | 说明                         |
|-------------|--------|------|--------|------------------------------|
| WorkflowUrl | string | 是   | -      | GitHub 工作流运行链接        |
| Token       | string | 否   | 自动   | GitHub Personal Access Token |

## 输出目录结构

```
local_data/logs/
└── {YYYY-MM-DD}/                        # 工作流运行日期（本地时间）
    └── {owner}-{repo}-{run_id}/         # 示例：sgl-project-sglang-26414786878
        ├── job-name-1.txt
        ├── job-name-2.txt
        └── download-summary.json
```

## Token 配置

将 GitHub Personal Access Token 放入以下文件：
```
local_data/github_token.txt
```

Token 需要 `repo` 权限。

## 输出示例

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

## 注意事项

- Token 文件：`local_data/github_token.txt`（需要 `repo` 权限）
- 日志按工作流运行的本地日期组织目录
- 下载失败时脚本会自动重试最多 3 次
- 支持大日志文件下载（300 秒超时）
