"""
classify-errors.py
对 outputs MM-DD 下的 run-dir 里的失败用例做根因分类.
从 ../../../config/analyzer.config.json 读取 context 行数配置.

命令行:
  --date MM-DD    outputs 下的子目录, 默认今日
  --root <path>   repo root, 默认脚本向上 2 级
  --run <name>    只处理指定 run 目录名
  --mode {case,job}  case=逐 case 分类失败原因 (默认); job=job 模式无 case 可分类, 直接跳过
  --out-dir <path>   直接指定 output_dir
"""
import argparse
import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def load_config():
    cfg_path = os.path.normpath(os.path.join(SCRIPT_DIR, "..", "..", "..", "config", "analyzer.config.json"))
    if not os.path.isfile(cfg_path):
        return {}
    try:
        with open(cfg_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


CONFIG = load_config()
CTX_BEFORE = int(CONFIG.get("context_lines_before", 5))
CTX_AFTER = int(CONFIG.get("context_lines_after", 25))
DETAIL_CTX_LINES = int(CONFIG.get("detailed_context_lines", 15))

ERROR_PATTERNS = [
    re.compile(r"(RuntimeError|AssertionError|ImportError|ModuleNotFoundError|TypeError|ValueError|KeyError|IndexError|AttributeError|NotImplementedError):\s*(.+)", re.IGNORECASE),
    re.compile(r"FAILED\s+\S*test_[a-zA-Z0-9_]+\s+-\s+(.+)"),
    re.compile(r"Error:\s*(.+)"),
    re.compile(r"exit code\s+(\d+)"),
    re.compile(r"No backend type associated with device type"),
    re.compile(r"torch\.compile.*?error", re.IGNORECASE),
    re.compile(r"CUDA|NPU.*?error", re.IGNORECASE),
    re.compile(r"Connection.*?timeout|timeout.*?connection", re.IGNORECASE),
    re.compile(r"ResourceExhaustedError|Resource exhausted", re.IGNORECASE),
    re.compile(r"OOM|out of memory|memory exhausted", re.IGNORECASE),
    re.compile(r"Device.*?not available|device not found", re.IGNORECASE),
    re.compile(r"SSH|runner.*?failed|runner disconnected", re.IGNORECASE),
    re.compile(r"docker.*?error|container.*?failed", re.IGNORECASE),
    re.compile(r"pytest.*?error|pytest.*?failed", re.IGNORECASE),
    re.compile(r"FileNotFoundError.*"),
    re.compile(r"Permission denied"),
    re.compile(r"No space left on device"),
    re.compile(r"Git clone failed|download.*?failed"),
]
ENVIRONMENT_KEYWORDS = [
    "OOM", "out of memory", "ResourceExhausted", "memory exhausted",
    "device not available", "NPU not found", "device not found",
    "runner", "SSH", "connection", "timeout",
    "docker", "container", "permission denied",
    "No space left", "runner disconnected",
    "failed to start container", "artifact download failed",
    "Git clone failed", "download failed",
]
TEST_CASE_KEYWORDS = [
    "FileNotFoundError", "test data", "fixture",
    "cannot collect test class", "pytest collection",
    "tolerance", "threshold too strict",
    "mock", "patch", "wrong parameter",
    "missing test data", "test config",
]
TIMESTAMP_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+Z\s*")
TYPE_CARD_PATTERN = re.compile(r'(nightly|full)-(\d+)')
NUMBER_IN_PAREN_PATTERN = re.compile(r'\((\d+)\)')


def get_pipeline_name(filename):
    m = TYPE_CARD_PATTERN.search(filename)
    if not m:
        return "unknown"
    base = f"{m.group(1)}-{m.group(2)}"
    n = NUMBER_IN_PAREN_PATTERN.search(filename)
    return f"{base}-({n.group(1)})" if n else base


def clean_line(line):
    return TIMESTAMP_PATTERN.sub("", line).rstrip()


def classify_error(error_text):
    e = error_text.lower()
    for kw in ENVIRONMENT_KEYWORDS:
        if kw.lower() in e:
            return "Environment"
    for kw in TEST_CASE_KEYWORDS:
        if kw.lower() in e:
            return "TestCase"
    for err in ["runtimeerror", "assertionerror", "importerror", "modulenotfounderror",
                "typeerror", "valueerror", "keyerror", "indexerror", "attributeerror",
                "notimplementederror", "backend", "kernel", "tensor", "shape mismatch",
                "invalid configuration", "compilation failed"]:
        if err in e:
            return "Product"
    return "Unclassified"


def find_test_error_in_file(file_path, test_name):
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
    except Exception:
        return "Could not read file", "", "Unclassified"

    best = -1
    for i, line in enumerate(lines):
        c = clean_line(line)
        if test_name in c and ("FAILED" in c or "ERROR" in c or "failed" in c.lower()):
            best = i; break
    if best == -1:
        for i, line in enumerate(lines):
            if test_name in line:
                best = i; break
    if best == -1:
        return "Test not found in log", "", "Unclassified"

    s = max(0, best - CTX_BEFORE)
    e = min(len(lines), best + CTX_AFTER)
    ctx = [clean_line(l) for l in lines[s:e] if clean_line(l).strip()]
    context = "\n".join(ctx)

    summary = "Unknown error"
    for line in ctx:
        for pat in ERROR_PATTERNS:
            m = pat.search(line)
            if m:
                summary = m.group(0); break
        if summary != "Unknown error":
            break
    return summary, context, classify_error(summary + " " + context)


def parse_failed_cases_from_report(run_dir):
    rp = os.path.join(run_dir, "analysis-report.txt")
    failed = []
    if not os.path.exists(rp):
        return scan_logs_directly(run_dir)
    in_list = False
    with open(rp, "r", encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if "[List] All Failed Cases:" in s:
                in_list = True; continue
            if in_list:
                if s.startswith("=") or not s:
                    break
                m = re.match(r"\s*\d+\.\s+(test_[a-zA-Z0-9_]+\.py)", s)
                if m:
                    case = m.group(1)
                    fn = find_log_file_for_case(run_dir, case)
                    pipe = get_pipeline_name(fn) if fn else "unknown"
                    failed.append((case, pipe, fn))
    return failed


def scan_logs_directly(run_dir):
    failed = []
    seen = set()
    for fn in os.listdir(run_dir):
        if not fn.endswith(".txt"):
            continue
        fp = os.path.join(run_dir, fn)
        try:
            content = open(fp, "r", encoding="utf-8", errors="ignore").read()
        except Exception:
            continue
        for m in re.finditer(r"FAILED\s+\S*/(test_[a-zA-Z0-9_]+\.py)", content):
            cn = m.group(1)
            if cn not in seen:
                seen.add(cn)
                failed.append((cn, get_pipeline_name(fn), fn))
    return failed


def find_log_file_for_case(run_dir, case_name):
    for fn in os.listdir(run_dir):
        if not fn.endswith(".txt"):
            continue
        fp = os.path.join(run_dir, fn)
        try:
            content = open(fp, "r", encoding="utf-8", errors="ignore").read()
        except Exception:
            continue
        if case_name in content:
            return fn
    return None


def gen_en(run_dir, failed, categories):
    eq80 = "=" * 80
    sep80 = "-" * 80
    lines = [
        eq80,
        "[Error Classification Report] NPU Nightly Test Failure Analysis",
        eq80,
        f"Analysis Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Log Directory: {run_dir}",
        f"Total Failed Cases: {len(failed)}",
        eq80,
        "",
        "[Summary] Failure Category Distribution",
        sep80,
    ]
    total = max(1, len(failed))
    for cat in ["Product", "TestCase", "Environment", "Unclassified"]:
        c = len(categories[cat])
        lines.append(f"{cat:20s}: {c:3d} ({c/total*100:5.1f}%)")
    lines.append(eq80)
    for cat in ["Product", "TestCase", "Environment", "Unclassified"]:
        items = categories[cat]
        if not items:
            continue
        lines += ["", f"[{cat} Issues] {len(items)} cases", sep80,
                  f"{'Case Name':<45s} | {'Pipeline':<15s} | {'Error Summary'}",
                  sep80]
        for it in items:
            lines.append(f"{it['case'][:44]:<45s} | {it['pipeline'][:14]:<15s} | {it['error'][:60]}")
        lines.append(eq80)
    lines += ["", "[Detailed Error Logs]", eq80]
    for d in categories.get("__detail__", []):
        lines += ["", f"### {d['case']} ({d['classification']} Issue)",
                  f"Pipeline: {d['pipeline']}",
                  f"Error: {d['error']}", "Context:"]
        ctx_lines = d['context'].split("\n")[:DETAIL_CTX_LINES] if d['context'] else []
        for cl in ctx_lines:
            lines.append(f"  {cl}")
        if not ctx_lines:
            lines.append("  (no context available)")
        lines.append("-" * 40)
    lines += [eq80, "[END] Classification Complete", eq80]
    return "\n".join(lines)


def gen_zh(run_dir, failed, categories):
    eq80 = "=" * 80
    sep80 = "-" * 80
    cn = {"Product": "产品（代码）问题", "TestCase": "用例问题",
          "Environment": "环境问题", "Unclassified": "未分类"}
    lines = [
        eq80,
        "[错误分类报告] NPU Nightly 测试失败分析",
        eq80,
        f"分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"日志目录: {run_dir}",
        f"总失败用例数: {len(failed)}",
        eq80,
        "",
        "[汇总] 失败分类分布",
        sep80,
    ]
    total = max(1, len(failed))
    for cat in ["Product", "TestCase", "Environment", "Unclassified"]:
        c = len(categories[cat])
        lines.append(f"{cn[cat]:20s}: {c:3d} ({c/total*100:5.1f}%)")
    lines.append(eq80)
    for cat in ["Product", "TestCase", "Environment", "Unclassified"]:
        items = categories[cat]
        if not items:
            continue
        lines += ["", f"[{cn[cat]}] {len(items)} 个用例", sep80,
                  f"{'用例名':<45s} | {'流水线':<15s} | {'错误摘要'}",
                  sep80]
        for it in items:
            lines.append(f"{it['case'][:44]:<45s} | {it['pipeline'][:14]:<15s} | {it['error'][:60]}")
        lines.append(eq80)
    lines += ["", "[END] 分类完成", eq80]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default="")
    parser.add_argument("--root", default="")
    parser.add_argument("--run", default="")
    parser.add_argument("--out-dir", default="")
    parser.add_argument("--mode", default="case", choices=["case", "job"], help="job 模式: 无 case 可分类, 跳过")
    args = parser.parse_args()

    if args.out_dir:
        output_dir = args.out_dir
    else:
        repo_root = args.root or os.path.normpath(os.path.join(SCRIPT_DIR, "..", ".."))
        month_day = args.date or datetime.now().strftime("%m-%d")
        output_dir = os.path.join(repo_root, "outputs", month_day)

    if args.mode == "job":
        # job 模式没有 case 失败可分类
        print(f"[classifier] mode=job, skip case-level error classification (output_dir={output_dir})")
        for run_dir in os.listdir(output_dir) if os.path.isdir(output_dir) else []:
            full = os.path.join(output_dir, run_dir)
            if os.path.isdir(full) and any(x.endswith(".txt") for x in os.listdir(full)):
                # 写一份最小占位报告, 保持 run_all 调用方逻辑一致
                for fn in ("error-classification-report.txt", "error-classification-report-zh.txt"):
                    p = os.path.join(full, fn)
                    if not os.path.isfile(p):
                        with open(p, "w", encoding="utf-8") as f:
                            f.write("[classifier] job-mode: no case-level error classification.\n")
        print("[classifier] DONE (skipped, job mode)")
        return

    if not os.path.isdir(output_dir):
        print(f"[classifier] ERROR: outputs dir not found: {output_dir}")
        sys.exit(1)

    run_dirs = []
    for fn in os.listdir(output_dir):
        p = os.path.join(output_dir, fn)
        if os.path.isdir(p) and any(x.endswith(".txt") for x in os.listdir(p)):
            run_dirs.append(p)
    if args.run:
        run_dirs = [d for d in run_dirs if os.path.basename(d) == args.run]
    if not run_dirs:
        print(f"[classifier] ERROR: no run dirs under {output_dir}")
        sys.exit(1)

    print(f"[classifier] output_dir: {output_dir}")
    for run_dir in run_dirs:
        print(f"[classifier] processing: {os.path.basename(run_dir)}")
        failed = parse_failed_cases_from_report(run_dir)
        print(f"[classifier]   failed cases: {len(failed)}")
        if not failed:
            print("[classifier]   nothing to classify, skip")
            continue

        categories = defaultdict(list)
        details = []
        for case, pipe, fn in failed:
            if fn:
                fp = os.path.join(run_dir, fn)
                es, ctx, cls = find_test_error_in_file(fp, case)
            else:
                es, ctx, cls = "Log file not found", "", "Unclassified"
            item = {"case": case, "pipeline": pipe, "error": es, "context": ctx}
            categories[cls].append(item)
            details.append({"case": case, "pipeline": pipe,
                            "classification": cls, "error": es, "context": ctx})
        categories["__detail__"] = details

        en_path = os.path.join(run_dir, "error-classification-report.txt")
        zh_path = os.path.join(run_dir, "error-classification-report-zh.txt")
        with open(en_path, "w", encoding="utf-8") as f:
            f.write(gen_en(run_dir, failed, categories))
        with open(zh_path, "w", encoding="utf-8") as f:
            f.write(gen_zh(run_dir, failed, categories))
        print(f"[classifier]   en: {en_path}")
        print(f"[classifier]   zh: {zh_path}")
        total = max(1, len(failed))
        for cat in ["Product", "TestCase", "Environment", "Unclassified"]:
            c = len(categories[cat])
            print(f"[classifier]   {cat:14s}: {c:3d} ({c/total*100:5.1f}%)")

    print("[classifier] DONE")


if __name__ == "__main__":
    main()
