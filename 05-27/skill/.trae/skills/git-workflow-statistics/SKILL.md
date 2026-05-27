---
name: GitHub Actions 工作流统计
version: 1.0.0
author: Trae AI
description: 获取 GitHub Actions 工作流运行记录，支持按时间范围过滤、分页获取，并生成统计报告。
tags:
  - github
  - actions
  - workflow
  - statistics
  - report

parameters:
  - name: repo
    type: string
    required: true
    default: sgl-project/sglang
    description: GitHub 仓库名称，格式为 "owner/repo"

  - name: workflow_id
    type: string
    required: true
    default: pr-test-npu.yml
    description: 工作流 ID 或文件名

  - name: start_date
    type: string
    required: false
    description: 开始日期，格式为 "yyyy-MM-dd"，默认为 7 天前

  - name: end_date
    type: string
    required: false
    description: 结束日期，格式为 "yyyy-MM-dd"，默认为今天

  - name: output_dir
    type: string
    required: false
    default: local_data/logs
    description: 输出目录路径

  - name: max_pages
    type: integer
    required: false
    default: 50
    description: 最大获取页数

steps:
  - name: 检查参数
    description: 验证输入参数
    action: |
      if (-not $repo) {
          $repo = "sgl-project/sglang"
      }
      if (-not $workflow_id) {
          $workflow_id = "pr-test-npu.yml"
      }

  - name: 执行统计脚本
    description: 调用工作流统计工具获取数据并生成报告
    action: |
      $scriptPath = "D:\personal_code\My-agent-assistant\git-workflow-statistics\git-workflow-statistics.ps1"
      
      $args = @(
          "-Repo", $repo,
          "-WorkflowId", $workflow_id,
          "-OutputDir", $output_dir,
          "-MaxPages", $max_pages
      )
      
      if ($start_date) {
          $args += "-StartDate", $start_date
      }
      if ($end_date) {
          $args += "-EndDate", $end_date
      }
      
      & powershell -ExecutionPolicy Bypass -File $scriptPath @args

  - name: 输出结果
    description: 显示执行结果
    action: |
      Write-Host "`n========================================" -ForegroundColor Green
      Write-Host "工作流统计任务完成！" -ForegroundColor Green
      Write-Host "========================================" -ForegroundColor Green
      Write-Host "`n📁 输出目录: $output_dir" -ForegroundColor Cyan
      Write-Host "`n提示: 报告文件格式为 workflow-stats_<时间戳>.(csv|md)" -ForegroundColor Gray

examples:
  - name: 获取默认时间范围的工作流统计
    description: 获取最近 7 天的 PR 测试工作流记录
    parameters: {}

  - name: 获取指定时间范围的工作流统计
    description: 获取 2026 年 5 月 18 日至 25 日的工作流记录
    parameters:
      start_date: "2026-05-18"
      end_date: "2026-05-25"

  - name: 获取其他仓库的工作流统计
    description: 获取其他仓库的工作流记录
    parameters:
      repo: "octocat/hello-world"
      workflow_id: "ci.yml"
      start_date: "2026-05-01"
      end_date: "2026-05-31"
      max_pages: 100

requirements:
  - 系统: Windows
  - PowerShell 版本: 5.1 或更高
  - 网络: 需要访问 GitHub API
  - 认证: 需要 GitHub Personal Access Token，存储在 local_data/github_token.txt

notes:
  - GitHub API 有请求频率限制，建议合理控制调用频率
  - 对于大量历史记录，可能需要增加 max_pages 参数
  - Token 文件应妥善保管，不要提交到版本控制
  - 建议将 local_data 目录添加到 .gitignore
