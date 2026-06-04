scripts/find_workflow
====================

`nightl-log-reporter` 流水线的第 ① 步：读配置、调用 GitHub REST API 找
匹配条件的 workflow run、把结果写成下游可读的 `workflow-info.json`。

---

文件清单
--------

| 文件 | 作用 |
|---|---|
| `find-workflow.ps1`        | 主脚本。读 `config\finder.config.json`，调 `/repos/{owner}/{repo}/actions/workflows/{id}/runs`，按 branch/event/date 过滤后写 `<out_dir>\workflow-info.json`。 |
| `utils\time-utils.ps1`     | 本地日期 ↔ UTC 区间换算工具（`Get-DateRangeUtc`、`Get-DateRangeUtcFromStartEnd`）。 |

---

用法
----

```powershell
# 在仓库根目录，用默认配置（今天，单 target 模式）
.\scripts\find_workflow\find-workflow.ps1

# 显式传参
.\scripts\find_workflow\find-workflow.ps1 `
    -ConfigPath   .\config\finder.config.json `
    -OutDir       .\outputs\06-04 `
    -Date         "2026-06-03" `
    -WorkflowUrl  "https://github.com/sgl-project/sglang/actions/workflows/nightly-test-npu.yml"
```

平时 `run_all.ps1` 会带好参数来调它，一般不需要直接手动跑。

---

配置（`config\finder.config.json`）
---------------------------------

```json
{
  "workflow_url": "https://github.com/sgl-project/sglang/actions/workflows/nightly-test-npu.yml",
  "branch": "main",
  "event":  "schedule",
  "date":   "",            // yyyy-MM-dd；空 = 今日
  "start_date": "",        // 可选；start_date + end_date 同时填则用区间模式
  "end_date":   "",
  "max_pages":  5          // GitHub API 分页上限，5*100=500 个 run
}
```

| 字段 | 含义 |
|---|---|
| `workflow_url` | Actions 工作流 URL（用来解析 owner/repo/workflow 文件名）。 |
| `branch`       | 只保留这个 branch 的 run（空 = 不过滤）。 |
| `event`        | 只保留这个 event 的 run（`schedule` / `push` / `workflow_dispatch` …）。 |
| `date`         | `yyyy-MM-dd`，空 = 今日。 |
| `start_date` / `end_date` | 区间模式；同时填三个字段时以区间为准。 |
| `max_pages`    | 最多翻多少页（每页 100 条）。 |

---

输出
----

`<out_dir>\workflow-info.json`：

```json
{
  "generated_at": "2026-06-04 14:29:03",
  "config":  { "workflow_url": "...", "branch": "main", "event": "schedule", "date": "2026-06-04" },
  "runs": [
    {
      "id": 26907746244,
      "url": "https://github.com/sgl-project/sglang/actions/runs/26907746244",
      "repo": "sgl-project/sglang",
      "owner": "sgl-project",
      "repo_name": "sglang",
      "workflow_id": "nightly-test-npu.yml",
      "branch": "main",
      "event": "schedule",
      "status": "completed",
      "conclusion": "success",
      "utc_created": "2026-06-04T12:00:00Z",
      "local_created": "2026-06-04 20:00:00",
      "local_date": "2026-06-04"
    }
  ]
}
```

默认输出目录是 `<repo_root>\outputs\<MM-DD>\`（`<MM-DD>` 由当前 `date` /
区间算出）；多 target 模式下 `run_all.ps1` 会显式传 `-OutDir` 到每个
target 自己的子目录。

---

GitHub token
------------

脚本会按以下顺序找 PAT：

1. `<repo_root>\local_data\github_token.txt`
2. `D:\personal_code\My-agent-assistant\local_data\github_token.txt`

PAT 需要 `repo` 和 `actions:read` 权限（私有仓库还需要对应访问权限）。

---

错误处理
--------

出错时脚本会把错误信息写到 `<repo_root>\logs\finder-last-error.txt`，
`run_all.ps1` 在调用后检查这个文件，存在就立刻中断整次跑批。
