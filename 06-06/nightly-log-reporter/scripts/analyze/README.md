# scripts/analyze

Step ③ of the `nightly-log-reporter` pipeline. Walks the run directories
produced by `download_log` and produces:

- An English / Chinese test-case report (mode `case`).
- A per-job pass-rate report (mode `job`).
- An error-classification report (which root-cause bucket each failed
  case belongs to: `Product` / `Environment` / `TestCase` / `Unclassified`).
- A small `analysis-brief.json` that the `summary/` step aggregates.

Two analyzer modes are supported, picked by the
`analyzer.mode` field in `targets.config.json` (default `case`).

| mode | granularity | input | used for |
|---|---|---|---|
| `case` | parse `Test Summary: N/M passed` blocks in the log | local `.txt` | `sglang` nightly (and other repos that print pytest summaries) |
| `job`  | GitHub Jobs API conclusion (`success` / `failure` / ...) | API call | `sgl-kernel-npu` daily-build (no test-summary blocks) |

---

## Files

| file | role |
|---|---|
| `analyze-log.py` | Generates `analysis-report.txt` / `analysis-report-zh.txt` and `analysis-brief.json`. Two modes: `case` (parse logs) and `job` (call API). |
| `classify-errors.py` | Reads the analysis report + raw logs, classifies each failed case into `Product` / `Environment` / `TestCase` / `Unclassified`, writes `error-classification-report[-zh].txt`. |

---

## Usage (standalone)

```powershell
# today's outputs, repo root
python scripts\analyze\analyze-log.py

# explicit outputs dir (multi-target: pass <root>\outputs\MM-DD\<target>)
python scripts\analyze\analyze-log.py --out-dir .\outputs\06-04\sglang-npu --mode case

# job mode (needs GitHub token)
python scripts\analyze\analyze-log.py --out-dir .\outputs\06-04\sgl-kernel-npu --mode job
```

```powershell
python scripts\analyze\classify-errors.py --out-dir .\outputs\06-04\sglang-npu --mode case
```

`run_all.ps1` calls both for each target with the right `--mode`.

---

## CLI reference

### `analyze-log.py`

| flag | default | meaning |
|---|---|---|
| `--out-dir`   | `<root>/outputs/<MM-DD>` | Output root. In multi-target mode this is `<root>/outputs/<MM-DD>/<target>`. |
| `--mode`      | `case` | `case` (parse logs) or `job` (call GitHub API). |
| `--date`      | today  | `MM-DD` subdir under `outputs/`. |
| `--root`      | script-up 2 levels | Repo root. |
| `--run`       | (all) | Only analyze the named run dir (e.g. `sgl-project-sglang-26907746244`). |
| `--token-path`| (auto) | GitHub PAT path; required for `--mode job`. |

### `classify-errors.py`

| flag | default | meaning |
|---|---|---|
| `--out-dir` | `<root>/outputs/<MM-DD>` | Output root (same as `analyze-log.py`). |
| `--mode`    | `case` | Mirrors `analyze-log.py`. In `job` mode there is no per-case data, so the script is a no-op. |
| `--date`    | today  | `MM-DD` subdir. |
| `--root`    | script-up 2 levels | Repo root. |
| `--run`     | (all)  | Only classify the named run dir. |

---

## Config (`config\analyzer.config.json`)

```json
{
  "context_lines_before":    5,
  "context_lines_after":     25,
  "detailed_context_lines":  15,
  "languages": ["en", "zh"]
}
```

These knobs control how many surrounding log lines `classify-errors.py`
prints around each failure when building the context window. They have no
effect on `analyze-log.py`.

---

## Outputs (per run dir)

```
<run-dir>\
├── *.txt                         (raw job logs, from step ②)
├── analysis-report.txt           (English report)
├── analysis-report-zh.txt        (Chinese report)
├── analysis-brief.json           (machine-readable: {mode, total, passed, failed, pass_rate})
├── error-classification-report.txt
└── error-classification-report-zh.txt
```

`analysis-brief.json` is the contract the `summary/` step reads.

---

## Classification buckets

`classify-errors.py` puts each failed case into one of:

| bucket | meaning |
|---|---|
| `Product` | Looks like a real product bug (assertion, kernel/tensor/shape, internal config, etc.). |
| `Environment` | Runner / network / disk / OOM / docker / git-clone / etc. |
| `TestCase` | Fixture / mock / threshold / test-data issue. |
| `Unclassified` | Couldn't decide; needs human review. |
