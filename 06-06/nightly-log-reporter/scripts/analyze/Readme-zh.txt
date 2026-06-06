scripts/analyze
===============

`nightly-log-reporter` 流水线的第 ③ 步。遍历 `download_log` 产出的各 run
目录，生成：

- 中英双语的 case 维度的分析报告（`case` 模式）。
- 按 job 的通过率报告（`job` 模式）。
- 失败用例的错误根因分类报告（`Product` / `Environment` / `TestCase` / `Unclassified`）。
- 一份 `analysis-brief.json`，供 `summary/` 步骤汇总。

支持两种分析模式，由 `targets.config.json` 里的 `analyzer.mode` 决定（默认 `case`）。

| 模式 | 粒度 | 数据来源 | 适用 |
|---|---|---|---|
| `case` | 解析日志里的 `Test Summary: N/M passed` 块 | 本地 `.txt` | `sglang` nightly（以及其他会打 pytest summary 的仓库） |
| `job`  | GitHub Jobs API 的 `conclusion`（`success` / `failure` / ...） | API | `sgl-kernel-npu` daily-build（没有 test-summary） |

---

文件清单
--------

| 文件 | 作用 |
|---|---|
| `analyze-log.py`     | 生成 `analysis-report.txt` / `analysis-report-zh.txt` 和 `analysis-brief.json`。两种模式：`case`（解析日志）和 `job`（调 API）。 |
| `classify-errors.py` | 读分析报告 + 原始日志，把每个失败 case 分到 `Product` / `Environment` / `TestCase` / `Unclassified` 一类，输出 `error-classification-report[-zh].txt`。 |

---

单独使用
--------

```powershell
# 今日产物，仓库根目录
python scripts\analyze\analyze-log.py

# 显式 output_dir（多 target 模式传 <root>\outputs\MM-DD\<target>）
python scripts\analyze\analyze-log.py --out-dir .\outputs\06-04\sglang-npu --mode case

# job 模式（需要 GitHub token）
python scripts\analyze\analyze-log.py --out-dir .\outputs\06-04\sgl-kernel-npu --mode job
```

```powershell
python scripts\analyze\classify-errors.py --out-dir .\outputs\06-04\sglang-npu --mode case
```

`run_all.ps1` 会按 target 顺序调这两个脚本，并传对应的 `--mode`。

---

命令行参数
----------

### `analyze-log.py`

| 参数 | 默认 | 含义 |
|---|---|---|
| `--out-dir`   | `<root>/outputs/<MM-DD>` | 输出根目录。多 target 模式下传 `<root>/outputs/<MM-DD>/<target>`。 |
| `--mode`      | `case` | `case`（扫日志）或 `job`（调 GitHub API）。 |
| `--date`      | 今日   | `outputs/` 下的 `MM-DD` 子目录。 |
| `--root`      | 脚本向上 2 级 | 仓库根目录。 |
| `--run`       | 全部   | 只分析指定 run 目录（如 `sgl-project-sglang-26907746244`）。 |
| `--token-path`| 自动   | GitHub PAT 路径；`--mode job` 时必填。 |

### `classify-errors.py`

| 参数 | 默认 | 含义 |
|---|---|---|
| `--out-dir` | `<root>/outputs/<MM-DD>` | 输出根目录（和 `analyze-log.py` 保持一致）。 |
| `--mode`    | `case` | 镜像 `analyze-log.py` 的 mode。`job` 模式没有 case 数据，脚本是空操作。 |
| `--date`    | 今日   | `outputs/` 下的 `MM-DD` 子目录。 |
| `--root`    | 脚本向上 2 级 | 仓库根目录。 |
| `--run`     | 全部   | 只对指定 run 目录做分类。 |

---

配置（`config\analyzer.config.json`）
-----------------------------------

```json
{
  "context_lines_before":    5,
  "context_lines_after":     25,
  "detailed_context_lines":  15,
  "languages": ["en", "zh"]
}
```

这些参数控制 `classify-errors.py` 在收集失败上下文时打印前后多少行
日志，对 `analyze-log.py` 无影响。

---

输出（每个 run 目录下）
----------------------

```
<run-dir>\
├── *.txt                         (第 ② 步下载的原始日志)
├── analysis-report.txt           (英文报告)
├── analysis-report-zh.txt        (中文报告)
├── analysis-brief.json           (机器可读: {mode, total, passed, failed, pass_rate})
├── error-classification-report.txt
└── error-classification-report-zh.txt
```

`analysis-brief.json` 是 `summary/` 步骤消费的契约文件。

---

错误分类桶
----------

`classify-errors.py` 把每个失败用例分到以下桶之一：

| 桶 | 含义 |
|---|---|
| `Product`       | 看起来像真正的产品 bug（assertion、kernel/tensor/shape、内部配置等）。 |
| `Environment`   | runner / 网络 / 磁盘 / OOM / docker / git-clone 等环境问题。 |
| `TestCase`      | fixture / mock / threshold / 测试数据问题。 |
| `Unclassified`  | 没法判断，需要人工看一眼。 |
