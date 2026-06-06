scripts/summary
==============

`nightly-log-reporter` 流水线的第 ④ 步。把每个 target 的
`analysis-brief.json` 汇总成一份人读的简报，写到
`<outputs>/<MM-DD>/summary.txt`。

每一行的格式取决于对应 target 的 `analyzer.mode`：

| analyzer mode | 行格式 |
|---|---|
| `case` | `label：通过率X% (执行用例N, 通过用例N, 失败用例N)` |
| `job`  | `label：通过率X% (执行job N, 通过job N, 失败job N)` |

`label` 取自 `targets.config.json → targets[i].label`（缺省回退到
`name`）。

---

文件清单
--------

| 文件 | 作用 |
|---|---|
| `build_summary.py` | 扫 `<out-dir>` 下所有 `analysis-brief.json`，按 target 合并，格式化后写 `summary.txt`。 |

---

用法
----

```powershell
# 默认：<repo_root>/outputs/<MM-DD>
python scripts\summary\build_summary.py

# 显式 output_dir（多 target 模式）
python scripts\summary\build_summary.py --out-dir .\outputs\06-04 --targets-config .\config\targets.config.json
```

`run_all.ps1` 在 analyze + classify 之后调这个脚本。

---

命令行参数
----------

| 参数 | 默认 | 含义 |
|---|---|---|
| `--out-dir`        | `<root>/outputs/<MM-DD>` | 包着 target 子目录的输出根目录。 |
| `--date`           | 今日   | `outputs/` 下的 `MM-DD` 子目录。 |
| `--root`           | 脚本向上 3 级 | 仓库根目录。 |
| `--targets-config` | `config/targets.config.json` | 读 `label` 映射的配置文件。 |
| `--title`          | `Nightly流水线` | 简报首行的标题。 |

---

输出
----

`<out-dir>/summary.txt`：

```
Nightly流水线：
kernel：通过率100.0% (执行job 8, 通过job 8, 失败job 0)
sglang：通过率87.2% (执行用例86, 通过用例75, 失败用例11)
```

脚本会做按 target 合并：同一个 target 多个 run 目录（比如同一天同一
workflow 多次 `schedule` 触发）时，`total` / `passed` / `failed` 先
累加再算通过率，每个 target 仍然只出现一行。

---

布局发现规则
------------

`find_briefs` 会同时认两种布局：

- 单 target：`<out-dir>/<run-dir>/analysis-brief.json`
- 多 target：`<out-dir>/<target>/<run-dir>/analysis-brief.json`

两者都没扫到时打 WARN 并以 0 退出（不写 `summary.txt`）。
