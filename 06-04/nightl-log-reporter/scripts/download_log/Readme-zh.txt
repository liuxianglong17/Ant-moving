scripts/download_log
====================

`nightl-log-reporter` 流水线的第 ② 步：读 `find_workflow` 产出的
`workflow-info.json`，对每个匹配 run 通过 GitHub Jobs API 下载所有 job
的纯文本日志，最后写 `download-summary.json` 供下游分析找到各 run 的目录。

---

文件清单
--------

| 文件 | 作用 |
|---|---|
| `download-log.ps1` | 主脚本。先拉每个 run 的 jobs 列表（`/repos/{owner}/{repo}/actions/runs/{id}/jobs`），再对每个 job 下载 `/actions/jobs/{job_id}/logs` 到 `<owner>-<repo>-<run_id>\` 目录。 |

---

用法
----

```powershell
# 默认：读 repo 根目录 outputs\MM-DD\workflow-info.json + 写到 outputs\MM-DD\
.\scripts\download_log\download-log.ps1

# 显式（多 target 模式，run_all.ps1 会这么调）
.\scripts\download_log\download-log.ps1 `
    -ConfigPath .\config\downloader.config.json `
    -InfoPath   .\outputs\06-04\sglang-npu\workflow-info.json `
    -OutDir     .\outputs\06-04\sglang-npu `
    -Repo       "sgl-project/sglang"
```

`run_all.ps1` 会在 `find-workflow.ps1` 跑完之后，对每个 target 调一次。

---

配置（`config\downloader.config.json`）
-------------------------------------

```json
{
  "repo":        "sgl-project/sglang",   // owner/repo；多 target 模式下会被 -Repo 覆盖
  "timeout_sec": 300,                    // 单次请求超时
  "max_retries": 3                       // 失败重试次数（中间 sleep 5s）
}
```

多 target 模式下 `run_all.ps1` 会根据 `targets.config.json` 在
`logs\.tmp\<timestamp>\downloader.<target>.json` 里生成对应的临时配置。

---

输出布局
--------

对 `workflow-info.json` 里的每个 run 各开一个目录：

```
<OutDir>\
├── download-summary.json
└── <owner>-<repo>-<run_id>\
    ├── <job1>.txt       (job 原始日志)
    ├── <job2>.txt
    └── ...
```

`download-summary.json` 是规范化的产物记录：

```json
{
  "repo": "sgl-project/sglang",
  "downloaded_at": "2026-06-04 14:30:01",
  "total_runs": 1,
  "total_downloaded": 7,
  "total_failed": 0,
  "runs": [
    {
      "run_id": 26907746244,
      "run_url": "https://github.com/sgl-project/sglang/actions/runs/26907746244",
      "branch": "main",
      "event":  "schedule",
      "local_created": "2026-06-04 20:00:00",
      "total_jobs": 7,
      "downloaded": 7,
      "failed":     0,
      "output_dir": "...\\outputs\\06-04\\sglang-npu\\sgl-project-sglang-26907746244"
    }
  ]
}
```

注意：如果 `workflow-info.json` 里 `runs` 为空，下载器会直接干净退出（不写
`download-summary.json`），表示“今天没有要下载的 run”。

---

GitHub token
------------

和 finder 一样的查找顺序：

1. `<repo_root>\local_data\github_token.txt`
2. `D:\personal_code\My-agent-assistant\local_data\github_token.txt`

---

错误处理
--------

出错时把错误信息写到 `<repo_root>\logs\downloader-last-error.txt`，
`run_all.ps1` 检测到这个文件就立刻中断整次跑批。单 job 失败会按
`max_retries` 重试，最后统计到 `download-summary.json` 的 `failed`
字段；脚本本身只在出现基础设施类错误（找不到 info 文件、token 缺失等）
时才整体失败。
