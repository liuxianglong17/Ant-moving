"""
analyze-log.py
从 outputs MM-DD 下的 download-summary.json 读取本次下载的所有 run 目录,
对每个 run 目录生成 analysis-report.txt / analysis-report-zh.txt.

支持两种分析模式:
  --mode case  (默认) 扫描 .txt 中的 test case pass/fail 统计 (sglang nightly 用)
  --mode job           直接通过 GitHub API 读 jobs status, 按 job 统计通过率
                       (sgl-kernel-npu daily-build-test 用; 该工作流无 case 粒度)
  --date MM-DD                  指定 outputs 下的子目录 (默认今日)
  --root <path>                 覆盖 repo root (默认脚本位置向上 2 级)
  --run <owner>-<repo>-<run_id> 仅分析指定 run
  --out-dir <path>              直接指定 output_dir, 跳过 root/outputs/date 拼接
                                (多 target 模式: 直接传 <root>/outputs/<MM-DD>/<target>)
  --token-path <path>           GitHub token 路径 (job 模式需要)
"""
import argparse
import json
import os
import re
import sys
import urllib.request
import urllib.error
from datetime import datetime

# 路径定位
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def load_config():
    """从 ../../../config/analyzer.config.json 读取配置 (相对脚本)."""
    cfg_path = os.path.normpath(os.path.join(SCRIPT_DIR, "..", "..", "..", "config", "analyzer.config.json"))
    if not os.path.isfile(cfg_path):
        return {}
    try:
        with open(cfg_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


CONFIG = load_config()

# 正则
SUMMARY_PATTERN = re.compile(r"Test Summary: (\d+)/(\d+) passed")
DELIMITER = "============================================================"
TIMESTAMP_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+Z\s*")
TYPE_CARD_PATTERN = re.compile(r'(nightly|full)-(\d+)')
NUMBER_IN_PAREN_PATTERN = re.compile(r'\((\d+)\)')
SKIP_PATTERN = re.compile(r'Skipped (\d+) test\(s\):')
SKIP_CASE_PATTERN = re.compile(r'-\s*(/[^ ]+)\s+\(reason:\s*(.+)\)')


def parse_test_log(file_path):
    passed = total = 0
    success_cases = []
    failed_cases = []
    skipped_cases = []
    found_summary = record_cases = False
    in_passed = in_failed = in_skipped = False

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception:
        return 0, 0, [], [], []

    for line in lines:
        clean_line = TIMESTAMP_PATTERN.sub("", line).rstrip()
        strip_line = clean_line.strip()

        if "Skipped" in strip_line and "test(s):" in strip_line:
            in_skipped, in_passed, in_failed = True, False, False
            continue

        if in_skipped:
            if (" Enabled " in strip_line or strip_line.startswith("PASSED")
                    or strip_line.startswith("FAILED") or "test(s) (est total" in strip_line):
                in_skipped = False
                continue
            m = SKIP_CASE_PATTERN.match(strip_line)
            if m:
                skipped_cases.append((os.path.basename(m.group(1)), m.group(2)))
            continue

        if not found_summary:
            m = SUMMARY_PATTERN.search(clean_line)
            if m:
                passed, total = int(m.group(1)), int(m.group(2))
                found_summary = True
            continue

        if DELIMITER in line:
            if not record_cases:
                record_cases = True
            else:
                break
            continue

        if record_cases:
            if not strip_line:
                continue
            if "PASSED:" in clean_line:
                in_passed, in_failed = True, False; continue
            if "FAILED:" in clean_line:
                in_failed, in_passed = True, False; continue
            if in_passed and strip_line.startswith("/"):
                success_cases.append(os.path.basename(strip_line))
            if in_failed and strip_line.startswith("/"):
                failed_cases.append(os.path.basename(strip_line.split(" (")[0]))

    return passed, total, success_cases, failed_cases, skipped_cases


def get_pipeline_name(filename):
    m = TYPE_CARD_PATTERN.search(filename)
    if not m:
        return "unknown"
    base = f"{m.group(1)}-{m.group(2)}"
    n = NUMBER_IN_PAREN_PATTERN.search(filename)
    return f"{base}-({n.group(1)})" if n else base


def _build_report_lines(log_dir, header, header_kv, fail_label, skip_label,
                        none_label, table_case, table_pipeline, summary_kv,
                        list_fail_header, list_skip_header, list_skip_line,
                        ok_label, sep60="-" * 60, eq80="=" * 80):
    """统一的中/英文报告生成器. 所有面向用户的字符串由调用方传入以保持 i18n 灵活."""
    lines = []
    total_all = pass_all = skip_all = 0
    all_fails = []
    all_skipped = []

    lines.append(eq80)
    lines.append(header)
    lines.append(eq80)
    for k, v in header_kv:
        lines.append(f"{k}: {v}")
    lines.append(eq80)

    for filename in sorted(os.listdir(log_dir)):
        fp = os.path.join(log_dir, filename)
        if not (os.path.isfile(fp) and filename.endswith(".txt")):
            continue
        p, t, succ, fail, skipped = parse_test_log(fp)
        if t == 0 and not skipped:
            continue
        total_all += t
        pass_all += p
        skip_all += len(skipped)
        for c in fail:
            all_fails.append((c, "", filename))
        for c, r in skipped:
            all_skipped.append((c, r, filename))

        lines.append(f"\n[File] {filename}")
        lines.append(f"[Result] {p}/{t} passed")
        if skipped:
            lines.append(f"[Skip] {len(skipped)} case(s)")
        lines.append(sep60)
        lines.append("[OK] PASSED:")
        for c in succ:
            lines.append(f"  {c}")
        lines.append("\n[FAIL] FAILED:")
        if fail:
            for c in fail:
                lines.append(f"  {c}")
        else:
            lines.append(f"  {none_label}")
        if skipped:
            lines.append("\n[SKIP] SKIPPED:")
            for c, r in skipped:
                lines.append(f"  {c} (reason: {r})")
        lines.append(eq80)

    # Failed table
    lines.append("\n" + eq80)
    lines.append(fail_label)
    lines.append(eq80)
    lines.append(f"{table_case}\t\tNote\t\t{table_pipeline}")
    if all_fails:
        for case, _, fn in all_fails:
            lines.append(f"{case}\t\t\t{get_pipeline_name(fn)}")
    else:
        lines.append(ok_label)

    # Skipped table (deduplicated by case)
    unique_skipped = {}
    for case, reason, fn in all_skipped:
        if case not in unique_skipped:
            unique_skipped[case] = (reason, fn)

    lines.append("\n" + eq80)
    lines.append(skip_label)
    lines.append(eq80)
    lines.append(f"{table_case}\t\tNote\t\t{table_pipeline}")
    if unique_skipped:
        for case, (reason, fn) in unique_skipped.items():
            lines.append(f"{case}\t{reason}\t{get_pipeline_name(fn)}")
    else:
        lines.append(ok_label)

    # Summary
    lines.append("\n" + eq80)
    for k, v in summary_kv(total_all, pass_all, len(all_fails), len(unique_skipped), skip_all):
        lines.append(f"{k}: {v}")
    lines.append("")
    lines.append(list_fail_header)
    if all_fails:
        for i, (case, _, _) in enumerate(all_fails, 1):
            lines.append(f"{i:2d}. {case}")
    else:
        lines.append(ok_label)
    if unique_skipped:
        lines.append("")
        lines.append(list_skip_header)
        for i, (case, (reason, fn)) in enumerate(unique_skipped.items(), 1):
            lines.append(list_skip_line(i, case, reason, get_pipeline_name(fn)))
    else:
        lines.append("")
        lines.append(ok_label)
    lines.append(eq80)
    return "\n".join(lines), all_fails, total_all, pass_all


def generate_report_en(log_dir):
    return _build_report_lines(
        log_dir,
        header="[Analysis] GitHub Actions Test Log Analysis Report",
        header_kv=[
            ("Analysis Directory", log_dir),
            ("Analysis Time", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        ],
        fail_label="[Table] Failed Cases Table",
        skip_label="[Table] Skipped Cases Table",
        none_label="None",
        table_case="Case Name",
        table_pipeline="Pipeline Name",
        summary_kv=lambda t, p, f, s, sr: [
            ("[Summary] Global Statistics", ""),
            ("Total Executed Cases", t),
            ("Total Passed Cases", p),
            ("Total Failed Cases", f),
            ("Total Skipped Cases", f"{s} (deduplicated, raw: {sr})"),
        ],
        list_fail_header="[List] All Failed Cases:",
        list_skip_header="[List] All Skipped Cases (deduplicated):",
        list_skip_line=lambda i, c, r, pn: f"{i:2d}.\t{c}\t{r}\t{pn}",
        ok_label="[OK] No failed cases" if False else "[OK] None",
    )


def generate_report_zh(log_dir):
    return _build_report_lines(
        log_dir,
        header="[Analysis] GitHub Actions 测试日志分析报告",
        header_kv=[
            ("分析目录", log_dir),
            ("分析时间", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        ],
        fail_label="[Table] 失败用例表格",
        skip_label="[Table] 跳过用例表格",
        none_label="无",
        table_case="用例名",
        table_pipeline="流水线名",
        summary_kv=lambda t, p, f, s, sr: [
            ("[Summary] 全局统计结果", ""),
            ("总执行用例数", t),
            ("总成功用例数", p),
            ("总失败用例数", f),
            ("总跳过用例数", f"{s} (去重后, 原始: {sr})"),
        ],
        list_fail_header="[List] 全部失败用例清单:",
        list_skip_header="[List] 全部跳过用例清单 (去重后):",
        list_skip_line=lambda i, c, r, pn: f"{i:2d}.\t{c}\t{r}\t{pn}",
        ok_label="[OK] 无",
    )


def discover_run_dirs(output_dir):
    """
    扫描 output_dir 下所有子目录, 把含 .txt 的子目录作为 run 目录.
    支持两种 layout:
      - 单 target: <output_dir>/<owner>-<repo>-<run_id>/*.txt
      - 多 target: <output_dir>/<target_name>/<owner>-<repo>-<run_id>/*.txt
    注: download-summary.json 的 runs[].output_dir 字段在历史版本中可能存的是
    旧的绝对路径 (单 target 模式下被迁移到多 target 时), 这里不依赖它, 一律按
    目录结构扫描, 更稳.
    """
    runs = []
    if not os.path.isdir(output_dir):
        return runs

    def has_txt(p):
        try:
            return any(fn.endswith(".txt") for fn in os.listdir(p))
        except Exception:
            return False

    def maybe_add(p):
        if os.path.isdir(p) and has_txt(p):
            runs.append(p)

    # 1) 顶层子目录
    top_has_run_like = False
    for fn in os.listdir(output_dir):
        p = os.path.join(output_dir, fn)
        if not os.path.isdir(p):
            continue
        m = RUN_DIR_PATTERN.match(fn)
        if m and has_txt(p):
            # 直接命中 run-dir 形式
            runs.append(p)
            top_has_run_like = True
        elif m:
            top_has_run_like = True

    # 2) 嵌套子目录 (多 target layout: <output_dir>/<target>/<run-dir>)
    for fn in os.listdir(output_dir):
        p = os.path.join(output_dir, fn)
        if not os.path.isdir(p):
            continue
        for sub in os.listdir(p):
            sp = os.path.join(p, sub)
            if os.path.isdir(sp) and has_txt(sp) and sp not in runs:
                runs.append(sp)
    return runs


def get_github_token(token_path=""):
    """读 GitHub token. 多个候选路径 (与 PowerShell 端 find-workflow / download-log 一致)."""
    candidates = []
    if token_path:
        candidates.append(token_path)
    candidates += [
        os.path.join(SCRIPT_DIR, "..", "..", "local_data", "github_token.txt"),
        os.path.normpath(os.path.join(SCRIPT_DIR, "..", "..", "..", "local_data", "github_token.txt")),
        r"D:\personal_code\My-agent-assistant\local_data\github_token.txt",
    ]
    for p in candidates:
        try:
            with open(p, "r", encoding="utf-8") as f:
                tk = f.read().strip()
                if tk:
                    return tk, p
        except Exception:
            continue
    raise RuntimeError("GitHub token not found. Tried: " + ", ".join(candidates))


def fetch_jobs_via_api(owner, repo, run_id, token):
    """GET /repos/{owner}/{repo}/actions/runs/{run_id}/jobs (分页) -> [job dict]."""
    jobs = []
    page = 1
    while True:
        url = f"https://api.github.com/repos/{owner}/{repo}/actions/runs/{run_id}/jobs?per_page=100&page={page}"
        req = urllib.request.Request(url, headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "nightl-log-reporter",
        })
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        jobs.extend(data.get("jobs", []))
        if len(data.get("jobs", [])) < 100:
            break
        page += 1
        if page > 20:  # 安全上限
            break
    return jobs


RUN_DIR_PATTERN = re.compile(r"^(?P<owner>[\w.-]+?)-(?P<repo>[\w.-]+?)-(?P<run_id>\d+)$")


def get_owner_repo_from_summary(output_root, run_dir_name, default_owner_repo=None):
    """从 download-summary.json 找该 run 对应的 owner/repo (精确匹配, 优先).

    适用场景: repo 或 owner 名字本身带 '-', 单纯按目录名 split 解析会切错位
    (如 sgl-project/sgl-kernel-npu, run_dir 形式为 sgl-project-sgl-kernel-npu-<id>).
    download-summary.json 的 repo 字段在顶层 (单 repo), runs[] 元素里未必有.
    """
    summary_path = os.path.join(output_root, "download-summary.json")
    if not os.path.isfile(summary_path):
        return None
    try:
        with open(summary_path, "r", encoding="utf-8-sig") as f:
            sd = json.load(f)
    except Exception:
        return None
    # 顶层 repo 优先
    top_repo = sd.get("repo") or ""
    owner_repo = None
    if "/" in top_repo:
        owner_repo = top_repo.split("/", 1)
    # 如果顶层没有, 从 runs 里取
    if not owner_repo:
        for r in sd.get("runs", []):
            repo = r.get("repo") or ""
            if "/" in repo:
                owner_repo = repo.split("/", 1)
                break
    if not owner_repo:
        return None
    owner, repo = owner_repo
    return owner, repo


def parse_run_dir_name(name):
    """从 '<owner>-<repo>-<run_id>' 解析出 (owner, repo, run_id).

    不能用纯 regex 的 lazy 匹配: 对 'sgl-project-sgl-kernel-npu-26902067922'
    这类 owner 或 repo 含 '-' 的情况, 任何基于首段是 owner 的 split 都会错位.
    优先用 download-summary.json 里的 repo 字段 (精确), 失败时再按 split 兜底.
    """
    m = RUN_DIR_PATTERN.match(name)
    if not m:
        return None
    # 先尝试从同名 download-summary.json 里拿 (output_root = name 的父目录的父目录)
    # run_dir = output_root/<target>/<name>; 但更稳的方式: 调用方传 output_root 来查
    # 这里只兜底: 取 head 第一段当 owner, 剩下的当 repo (适用于 owner 单段的情况)
    cut = name.rsplit("-", 1)
    if len(cut) != 2 or not cut[1].isdigit():
        return None
    head, run_id = cut
    if "-" not in head:
        return None
    owner, _, repo = head.partition("-")
    if not owner or not repo:
        return None
    return owner, repo, run_id


def _build_job_report_lines(run_dir, run_id, jobs, lang="en"):
    """job 模式: 写一个简洁报告, 列出每个 job 的 status/conclusion, 给出通过率统计."""
    if lang == "zh":
        header = "[Analysis] Job 模式分析报告 (按 job 统计通过率)"
        label_result = "[结果]"
        label_total = "总 job 数"
        label_pass = "通过 job 数"
        label_fail = "失败 job 数"
        label_pending = "未完成 job 数"
        label_rate = "通过率"
        label_jobs = "[列表] Job 列表"
        label_ok = "[OK] 全部通过"
        no_data = "无 jobs 数据"
        time_label = "分析时间"
    else:
        header = "[Analysis] Job-mode Report (per-job pass rate)"
        label_result = "[Result]"
        label_total = "Total jobs"
        label_pass = "Passed jobs"
        label_fail = "Failed jobs"
        label_pending = "Pending jobs"
        label_rate = "Pass rate"
        label_jobs = "[List] Jobs"
        label_ok = "[OK] All passed"
        no_data = "no jobs data"
        time_label = "Analysis time"

    eq80 = "=" * 80
    sep60 = "-" * 60
    lines = [eq80, header, eq80]
    lines.append(f"Run directory: {run_dir}")
    lines.append(f"Run ID:        {run_id}")
    lines.append(f"{time_label}:  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(eq80)

    total = len(jobs)
    passed = sum(1 for j in jobs if j.get("conclusion") == "success")
    failed = sum(1 for j in jobs if j.get("conclusion") == "failure")
    pending = sum(1 for j in jobs if j.get("conclusion") not in ("success", "failure"))
    rate = (passed / total * 100.0) if total else 0.0

    if not jobs:
        lines.append(no_data)
    else:
        lines.append(label_jobs)
        for j in jobs:
            name = j.get("name", "")
            conc = j.get("conclusion") or j.get("status") or ""
            marker = "OK" if conc == "success" else ("FAIL" if conc == "failure" else "...")
            lines.append(f"  [{marker:4s}] {name}  ({conc})")
        lines.append(sep60)
        lines.append(f"{label_total}:   {total}")
        lines.append(f"{label_pass}:    {passed}")
        lines.append(f"{label_fail}:    {failed}")
        lines.append(f"{label_pending}: {pending}")
        lines.append(f"{label_rate}:   {rate:.1f}%")
    lines.append(eq80)
    return "\n".join(lines), {
        "total": total, "passed": passed, "failed": failed, "pending": pending, "rate": rate,
    }


def analyze_job_mode(run_dir, token):
    """job 模式分析: 调 GitHub API 读 jobs status, 写两份报告 + 简报 JSON."""
    name = os.path.basename(run_dir)
    parsed = parse_run_dir_name(name)
    # 优先用 download-summary.json 拿精确 owner/repo
    # run_dir = <output_dir>/<target>/<run_dir>  -> output_dir = parent of run_dir
    output_root = os.path.dirname(run_dir)
    summary_pair = get_owner_repo_from_summary(output_root, name)
    if summary_pair:
        owner, repo = summary_pair
        # run_id 仍用目录名解析 (split 兜底是可靠的: 最后一段 digits)
        _, _, run_id_str = name.rpartition("-")
        run_id = run_id_str
    elif parsed:
        owner, repo, run_id = parsed
    else:
        print(f"[analyzer] WARN: run dir name '{name}' doesn't match <owner>-<repo>-<run_id>, skip job-mode analysis")
        return None
    print(f"[analyzer]   job-mode: querying {owner}/{repo} run {run_id} ...")
    try:
        jobs = fetch_jobs_via_api(owner, repo, run_id, token)
    except urllib.error.HTTPError as e:
        print(f"[analyzer]   WARN: GitHub API HTTP {e.code} for {owner}/{repo}/{run_id}: {e.reason}")
        return None
    except Exception as e:
        print(f"[analyzer]   WARN: GitHub API call failed: {e}")
        return None

    # 过滤掉非测试收尾类 job (finish / finalize / complete 之类)
    excluded_names = {"finish", "finalize", "complete", "post-run", "setup", "teardown"}
    filtered = [j for j in jobs if (j.get("name") or "").strip().lower() not in excluded_names]
    excluded_count = len(jobs) - len(filtered)
    if excluded_count:
        print(f"[analyzer]   excluded {excluded_count} non-test job(s) (finish/finalize/...)")

    en, stats = _build_job_report_lines(run_dir, run_id, filtered, lang="en")
    zh, _ = _build_job_report_lines(run_dir, run_id, filtered, lang="zh")

    with open(os.path.join(run_dir, "analysis-report.txt"), "w", encoding="utf-8") as f:
        f.write(en)
    with open(os.path.join(run_dir, "analysis-report-zh.txt"), "w", encoding="utf-8") as f:
        f.write(zh)

    # 写一份简报 JSON 供合并简报脚本读
    brief = {
        "mode": "job",
        "owner": owner,
        "repo": repo,
        "run_id": run_id,
        "total": stats["total"],
        "passed": stats["passed"],
        "failed": stats["failed"],
        "pending": stats["pending"],
        "pass_rate": round(stats["rate"], 2),
    }
    with open(os.path.join(run_dir, "analysis-brief.json"), "w", encoding="utf-8") as f:
        json.dump(brief, f, ensure_ascii=False, indent=2)
    print(f"[analyzer]   jobs total={stats['total']} pass={stats['passed']} fail={stats['failed']} rate={stats['rate']:.1f}%")
    return brief


def analyze_case_mode(run_dir):
    """case 模式分析 (原有逻辑). 同时写 analysis-brief.json 供合并简报用."""
    report_en, all_fails, total, passed = generate_report_en(run_dir)
    with open(os.path.join(run_dir, "analysis-report.txt"), "w", encoding="utf-8") as f:
        f.write(report_en)
    print(f"[analyzer]   en: {os.path.join(run_dir, 'analysis-report.txt')}")

    report_zh, _, _, _ = generate_report_zh(run_dir)
    with open(os.path.join(run_dir, "analysis-report-zh.txt"), "w", encoding="utf-8") as f:
        f.write(report_zh)
    print(f"[analyzer]   zh: {os.path.join(run_dir, 'analysis-report-zh.txt')}")

    print(f"[analyzer]   total={total} passed={passed} failed={len(all_fails)}")

    brief = {
        "mode": "case",
        "total": total,
        "passed": passed,
        "failed": len(all_fails),
        "pass_rate": round((passed / total * 100.0) if total else 0.0, 2),
    }
    with open(os.path.join(run_dir, "analysis-brief.json"), "w", encoding="utf-8") as f:
        json.dump(brief, f, ensure_ascii=False, indent=2)
    return brief


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default="", help="outputs 下的子目录, 形如 06-04. 默认今日.")
    parser.add_argument("--root", default="", help="repo root 路径. 默认 = 脚本向上 2 级.")
    parser.add_argument("--run", default="", help="只分析指定 run 目录名 (如 sgl-project-sglang-12345678).")
    parser.add_argument("--out-dir", default="", help="直接指定 output_dir, 跳过 root/outputs/date 拼接.")
    parser.add_argument("--mode", default="case", choices=["case", "job"], help="case=扫 .txt 统计 case; job=按 job 状态统计.")
    parser.add_argument("--token-path", default="", help="GitHub token 路径 (job 模式).")
    args = parser.parse_args()

    if args.out_dir:
        output_dir = args.out_dir
    else:
        repo_root = args.root or os.path.normpath(os.path.join(SCRIPT_DIR, "..", ".."))
        month_day = args.date or datetime.now().strftime("%m-%d")
        output_dir = os.path.join(repo_root, "outputs", month_day)

    if not os.path.isdir(output_dir):
        print(f"[analyzer] ERROR: outputs dir not found: {output_dir}")
        sys.exit(1)

    run_dirs = discover_run_dirs(output_dir)
    if args.run:
        run_dirs = [d for d in run_dirs if os.path.basename(d) == args.run]
    if not run_dirs:
        print(f"[analyzer] ERROR: no run directories under {output_dir}")
        sys.exit(1)

    print(f"[analyzer] output_dir: {output_dir}")
    print(f"[analyzer] mode:       {args.mode}")
    print(f"[analyzer] run_dirs:   {len(run_dirs)}")

    token = None
    if args.mode == "job":
        try:
            token, _ = get_github_token(args.token_path)
        except Exception as e:
            print(f"[analyzer] ERROR: {e}")
            sys.exit(1)

    for run_dir in run_dirs:
        print(f"[analyzer]   - {os.path.basename(run_dir)}")
        if args.mode == "job":
            analyze_job_mode(run_dir, token)
        else:
            analyze_case_mode(run_dir)

    print("[analyzer] DONE")


if __name__ == "__main__":
    main()
