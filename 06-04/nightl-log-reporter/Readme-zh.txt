nightl-log-reporter
==================

GitHub Actions 工作流日志的**一键下载 + 分析**工具集
（目前用于 sgl-project/sglang nightly 和 sgl-project/sgl-kernel-npu daily，
但适用于任意 GitHub 仓库）。

支持 **单 target**（一个工作流）和 **多 target**（同一/不同仓库的多个工作流，
依次执行）两种模式。

---

1. 快速开始
-----------

### 1.1 一键入口（推荐）

```bat
:: cmd / 双击
run_all.bat
```

`run_all.bat` 内部用 `-ExecutionPolicy Bypass` 调 PowerShell，
因为 Windows 5.1 PowerShell 默认会拦截 `.ps1` 执行。

### 1.2 手动 PowerShell

```powershell
# 今日
.\run_all.ps1

# 指定日期 (写到 outputs\06-03\)
.\run_all.ps1 -Date 06-03

# 跳过某些步骤
.\run_all.ps1 -SkipFind
.\run_all.ps1 -SkipFind -SkipDownload
.\run_all.ps1 -SkipAnalyze
.\run_all.ps1 -SkipSummary
```

### 1.3 多 target 模式

```powershell
# 跑 config\targets.config.json 里的所有 target
.\run_all.ps1 -TargetsConfig .\config\targets.config.json

# 只跑其中一个 target
.\run_all.ps1 -TargetsConfig .\config\targets.config.json -Target sglang-npu
```

`run_all.ps1` 对每个 target 顺序执行 **find → download → analyze → classify → summary**；
任一 target 的任一步失败立刻终止（避免下游分析拿到不完整数据）。

---

2. 输出结构
-----------

### 2.1 单 target 布局

```
outputs\06-04\
├── workflow-info.json
├── download-summary.json
├── summary.txt                  # ← 由 build_summary.py 生成
└── <owner>-<repo>-<run_id>\
    ├── *.txt                    # 各 job 原始日志
    ├── analysis-report.txt      # 英文分析报告
    ├── analysis-report-zh.txt   # 中文分析报告
    ├── analysis-brief.json      # 简报 (机器可读)
    ├── error-classification-report.txt
    └── error-classification-report-zh.txt
```

### 2.2 多 target 布局

```
outputs\06-04\
├── summary.txt                  # 所有 target 的合并简报
├── sglang-npu\
│   ├── workflow-info.json
│   ├── download-summary.json
│   └── <owner>-<repo>-<run_id>\...
└── sgl-kernel-npu\
    └── ...
```

### 2.3 `summary.txt` 示例

```
Nightly流水线：
kernel：通过率100.0% (执行job 8, 通过job 8, 失败job 0)
sglang：通过率87.2% (执行用例86, 通过用例75, 失败用例11)
```

每个 target 按其 `analyzer.mode` 渲染：case 模式显示"执行用例"，job 模式显示"执行job"。
简报中显示的 label 取 `targets.config.json → label`（缺省 = `name`）。

---

3. 多 target 配置
-----------------

`config\targets.config.json`：

```json
{
  "targets": [
    {
      "name": "sglang-npu",
      "label": "sglang",
      "finder": {
        "workflow_url": "https://github.com/sgl-project/sglang/actions/workflows/nightly-test-npu.yml",
        "branch": "main",
        "event": "schedule",
        "date": "",
        "start_date": "",
        "end_date": "",
        "max_pages": 5
      },
      "downloader": {
        "repo": "sgl-project/sglang",
        "timeout_sec": 300,
        "max_retries": 3
      },
      "analyzer": { "mode": "case" }
    },
    {
      "name": "sgl-kernel-npu",
      "label": "kernel",
      "finder": {
        "workflow_url": "https://github.com/sgl-project/sgl-kernel-npu/actions/workflows/daily-build-test.yml",
        "branch": "main",
        "event": "schedule",
        "max_pages": 5
      },
      "downloader": { "repo": "sgl-project/sgl-kernel-npu" },
      "analyzer": { "mode": "job" }
    }
  ]
}
```

| 字段                | 含义                                                          |
|---------------------|---------------------------------------------------------------|
| `name`              | 唯一 key；也是 `outputs\MM-DD\<name>\` 子目录名               |
| `label`             | 简报里显示的名字（缺省 = `name`）                             |
| `finder.*`          | 同 `finder.config.json`                                       |
| `downloader.*`      | 同 `downloader.config.json`                                   |
| `analyzer.mode`     | `case`（默认，扫 .txt 统计 case）或 `job`（调 GitHub API 统计 job） |

---

4. 目录结构
-----------

```
nightl-log-reporter\
├── run_all.bat / run_all.ps1        # 入口
├── config\                          # 改这里就能换行为
│   ├── finder.config.json
│   ├── downloader.config.json
│   ├── targets.config.json
│   └── analyzer.config.json
├── scripts\
│   ├── find_workflow\               # ① 找 workflow run
│   │   ├── find-workflow.ps1
│   │   └── utils\time-utils.ps1
│   ├── download_log\                # ② 下载日志
│   │   └── download-log.ps1
│   ├── analyze\                     # ③ 分析 + 错误分类
│   │   ├── analyze-log.py
│   │   └── classify-errors.py
│   └── summary\                     # ④ 合并简报
│       └── build_summary.py
├── local_data\
│   └── github_token.txt             # ← 必填，PAT 需 `repo` + `actions:read`
├── outputs\MM-DD\                   # 当日产物
└── logs\                            # 跑批日志（调试用）
```

每个 `scripts\<step>\` 都有独立的 README，详看各自文档。

---

5. 首次使用
-----------

1. 准备一个 GitHub PAT，scope 至少包含 `repo` 和 `actions:read`。
2. 写到 `local_data\github_token.txt`（末尾不必留空行）。

之后直接 `run_all.bat` 即可。

---

6. 适配别的仓库
---------------

- **单 target 模式**：改 `config\finder.config.json` 的 `workflow_url`，
  改 `config\downloader.config.json` 的 `repo`。
- **多 target 模式**：在 `config\targets.config.json` 里增删 target。
- **换分析粒度**：把 `analyzer.mode` 设为 `job`（按 GitHub Job 数通过率，
  不扫日志）或 `case`（扫 `Test Summary: N/M passed` 块）。

---

7. 执行策略提示
---------------

Windows 5.1 PowerShell 默认策略会拦截 `.ps1`，三种绕法：

- `run_all.bat`（最省事，内部 `-ExecutionPolicy Bypass`）
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\run_all.ps1`
- 一次性放开：`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`
