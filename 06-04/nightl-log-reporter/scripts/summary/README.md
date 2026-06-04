# scripts/summary

Step ④ of the `nightl-log-reporter` pipeline. Aggregates each target's
`analysis-brief.json` into a single human-readable brief at
`<outputs>/<MM-DD>/summary.txt`.

The per-line format depends on each target's analyzer mode:

| analyzer mode | line format |
|---|---|
| `case` | `label：通过率X% (执行用例N, 通过用例N, 失败用例N)` |
| `job`  | `label：通过率X% (执行job N, 通过job N, 失败job N)` |

`label` comes from `targets.config.json → targets[i].label`
(falls back to the target's `name`).

---

## Files

| file | role |
|---|---|
| `build_summary.py` | Scans `<out-dir>` for `analysis-brief.json`, groups by target, formats and writes `summary.txt`. |

---

## Usage

```powershell
# default: <repo_root>/outputs/<MM-DD>
python scripts\summary\build_summary.py

# explicit output dir (multi-target)
python scripts\summary\build_summary.py --out-dir .\outputs\06-04 --targets-config .\config\targets.config.json
```

`run_all.ps1` calls this after the analyze + classify step.

---

## CLI

| flag | default | meaning |
|---|---|---|
| `--out-dir`         | `<root>/outputs/<MM-DD>` | Output root that contains the target subdirs. |
| `--date`            | today  | `MM-DD` subdir. |
| `--root`            | script-up 3 levels | Repo root. |
| `--targets-config`  | `config/targets.config.json` | Where to read `label` mappings from. |
| `--title`           | `Nightly流水线` | Header line written above the rows. |

---

## Output

`<out-dir>/summary.txt`:

```
Nightly流水线：
kernel：通过率100.0% (执行job 8, 通过job 8, 失败job 0)
sglang：通过率87.2% (执行用例86, 通过用例75, 失败用例11)
```

The script also groups: if a target has multiple run directories
(e.g. multiple `schedule` events on the same day for the same workflow),
their `total` / `passed` / `failed` are summed before the rate is
recomputed, so each target appears as a single line.

---

## Discovery rules

`find_briefs` walks two layouts:

- Single-target: `<out-dir>/<run-dir>/analysis-brief.json`
- Multi-target: `<out-dir>/<target>/<run-dir>/analysis-brief.json`

If neither has any briefs the script prints a warning and exits 0
(no `summary.txt` is written).
