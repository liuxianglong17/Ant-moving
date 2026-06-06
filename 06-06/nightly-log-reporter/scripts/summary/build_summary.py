"""
build_summary.py
合并简报脚本: 扫描 outputs/<MM-DD>/ 下所有 target 子目录, 读 analysis-brief.json,
按各 target 自身的简报格式生成合并简报:

  Nightly流水线：
  sglang：通过率86.0% (执行用例86, 通过用例74, 失败用例11)
  kernel：通过率100% (执行job 8, 通过job 8, 失败job 0)

简报逻辑按 mode 分:
  - mode=case: 通过率% (执行用例 N, 通过用例 N, 失败用例 N)
  - mode=job : 通过率% (执行job N, 通过job N, 失败job N)

target_name -> 简报中显示的 label 通过 targets.config.json 的 label 字段覆盖 (默认取 name).
"""
import argparse
import json
import os
import sys
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def load_targets_config(path):
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def find_briefs(output_dir):
    """扫 output_dir 下所有子目录, 找 analysis-brief.json.
    支持 layout:
      - 单 target:  <output_dir>/<run-dir>/analysis-brief.json
      - 多 target:  <output_dir>/<target>/<run-dir>/analysis-brief.json
      - 混合 (旧):  <output_dir>/<run-dir>/analysis-brief.json
    返回 list of (target_name, brief_dict, brief_path), target_name 优先取
    targets.config.json 的 label 字段, 缺省 = 最外层子目录名 (run-dir 或 target).
    """
    out = []
    if not os.path.isdir(output_dir):
        return out
    for fn in sorted(os.listdir(output_dir)):
        sub = os.path.join(output_dir, fn)
        if not os.path.isdir(sub):
            continue
        # 1) 顶层就是 run-dir
        brief_p = os.path.join(sub, "analysis-brief.json")
        if os.path.isfile(brief_p):
            out.append((fn, brief_p))
            continue
        # 2) 嵌套 target/run-dir
        for sub2 in sorted(os.listdir(sub)):
            sub2p = os.path.join(sub, sub2)
            if not os.path.isdir(sub2p):
                continue
            brief_p2 = os.path.join(sub2p, "analysis-brief.json")
            if os.path.isfile(brief_p2):
                out.append((fn, brief_p2))
    return out


def format_one_brief(brief, lang="zh"):
    """根据 brief 自身的 mode 字段决定简报格式."""
    mode = brief.get("mode", "case")
    rate = brief.get("pass_rate", 0.0)
    total = brief.get("total", 0)
    passed = brief.get("passed", 0)
    failed = brief.get("failed", 0)
    if mode == "job":
        return f"通过率{rate:.1f}% (执行job {total}, 通过job {passed}, 失败job {failed})"
    # case 模式
    return f"通过率{rate:.1f}% (执行用例{total}, 通过用例{passed}, 失败用例{failed})"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default="", help="outputs 下的子目录, 形如 06-04. 默认今日.")
    parser.add_argument("--root", default="", help="repo root 路径. 默认 = 脚本向上 3 级.")
    parser.add_argument("--out-dir", default="", help="直接指定 outputs 根 (含 MM-DD).")
    parser.add_argument("--targets-config", default="", help="targets.config.json 路径, 用于读 label 配置.")
    parser.add_argument("--title", default="Nightly流水线", help="简报标题.")
    args = parser.parse_args()

    if args.out_dir:
        output_root = args.out_dir
    else:
        repo_root = args.root or os.path.normpath(os.path.join(SCRIPT_DIR, "..", "..", ".."))
        month_day = args.date or datetime.now().strftime("%m-%d")
        output_root = os.path.join(repo_root, "outputs", month_day)

    if not os.path.isdir(output_root):
        print(f"[summary] ERROR: outputs dir not found: {output_root}")
        sys.exit(1)

    # 读 targets.config 拿 label 映射
    label_map = {}  # target_name -> label
    tcfg_path = args.targets_config or os.path.join(
        os.path.normpath(os.path.join(SCRIPT_DIR, "..", "..")), "config", "targets.config.json"
    )
    tcfg = load_targets_config(tcfg_path)
    for t in tcfg.get("targets", []) or []:
        name = t.get("name")
        label = t.get("label") or name
        if name:
            label_map[name] = label

    # 单 target 模式: briefs 可能在 output_root 本目录 (不是子目录) — 支持两种 layout
    briefs = find_briefs(output_root)
    # 同时, 单 target 模式 briefs 在 output_root/<run-dir>/analysis-brief.json, 这已经被 find_briefs 扫到.
    # 多 target 模式 briefs 在 output_root/<target>/<run-dir>/analysis-brief.json, 也被扫到.

    if not briefs:
        print(f"[summary] WARN: no analysis-brief.json found under {output_root}")

    # 加载所有 brief
    parsed = []  # [(target_name, brief)]
    for target_name, brief_p in briefs:
        try:
            with open(brief_p, "r", encoding="utf-8") as f:
                b = json.load(f)
        except Exception as e:
            print(f"[summary] WARN: failed to parse {brief_p}: {e}")
            continue
        parsed.append((target_name, b))

    # 按 target_name 分组: 同一 target 多个 run 目录, 简报里只显示一个总行.
    grouped = {}
    order = []
    for target_name, brief in parsed:
        mode = brief.get("mode", "case")
        if target_name not in grouped:
            grouped[target_name] = {"mode": mode, "total": 0, "passed": 0, "failed": 0, "pending": 0}
            order.append(target_name)
        g = grouped[target_name]
        g["total"] += int(brief.get("total", 0) or 0)
        g["passed"] += int(brief.get("passed", 0) or 0)
        g["failed"] += int(brief.get("failed", 0) or 0)
        g["pending"] += int(brief.get("pending", 0) or 0)
    for tn, g in grouped.items():
        rate = (g["passed"] / g["total"] * 100.0) if g["total"] else 0.0
        g["pass_rate"] = round(rate, 2)

    lines = []
    lines.append(args.title + "：")
    for tn in order:
        g = grouped[tn]
        label = label_map.get(tn, tn)
        brief_obj = {
            "mode": g["mode"],
            "total": g["total"],
            "passed": g["passed"],
            "failed": g["failed"],
            "pass_rate": g["pass_rate"],
        }
        one = format_one_brief(brief_obj, lang="zh")
        lines.append(f"{label}：{one}")

    summary_text = "\n".join(lines) + "\n"

    # 写到 outputs 根
    summary_path = os.path.join(output_root, "summary.txt")
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write(summary_text)
    print(f"[summary] output_root: {output_root}")
    print(f"[summary] targets:      {len(order)}")
    for tn in order:
        print(f"[summary]   - {tn}  mode={grouped[tn]['mode']}  total={grouped[tn]['total']}")
    print(f"[summary] summary.txt:  {summary_path}")
    print("---")
    print(summary_text, end="")
    print("---")
    print("[summary] DONE")


if __name__ == "__main__":
    main()
