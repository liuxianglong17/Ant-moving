import os
import re
import sys
from datetime import datetime
from collections import defaultdict

# 错误模式匹配
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

# 分类关键词
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
    type_card_match = TYPE_CARD_PATTERN.search(filename)
    if not type_card_match:
        return "unknown"
    test_type = type_card_match.group(1)
    card_num = type_card_match.group(2)
    base_name = f"{test_type}-{card_num}"
    number_match = NUMBER_IN_PAREN_PATTERN.search(filename)
    if number_match:
        num = number_match.group(1)
        return f"{base_name}-({num})"
    return base_name


def clean_line(line):
    return TIMESTAMP_PATTERN.sub("", line).rstrip()


def find_test_error_in_file(file_path, test_name):
    """
    Find error details for a specific test case in a log file.
    Returns (error_summary, error_context, classification)
    """
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
    except Exception:
        return "Could not read file", "", "Unclassified"

    # Find the line containing the test name in failure context
    best_match_idx = -1
    for i, line in enumerate(lines):
        clean = clean_line(line)
        if test_name in clean and ("FAILED" in clean or "ERROR" in clean or "failed" in clean.lower()):
            best_match_idx = i
            break

    if best_match_idx == -1:
        # Try broader search
        for i, line in enumerate(lines):
            if test_name in line:
                best_match_idx = i
                break

    if best_match_idx == -1:
        return "Test not found in log", "", "Unclassified"

    # Extract context window (20 lines after)
    start = max(0, best_match_idx - 5)
    end = min(len(lines), best_match_idx + 25)
    context_lines = [clean_line(l) for l in lines[start:end] if clean_line(l).strip()]
    context = "\n".join(context_lines)

    # Find specific error message
    error_summary = "Unknown error"
    for line in context_lines:
        for pattern in ERROR_PATTERNS:
            match = pattern.search(line)
            if match:
                error_summary = match.group(0)
                break
        if error_summary != "Unknown error":
            break

    # Classify the error
    classification = classify_error(error_summary + " " + context)

    return error_summary, context, classification


def classify_error(error_text):
    """
    Classify error into: Product, TestCase, Environment, or Unclassified
    """
    error_lower = error_text.lower()

    # Check environment keywords first
    for kw in ENVIRONMENT_KEYWORDS:
        if kw.lower() in error_lower:
            return "Environment"

    # Check test case keywords
    for kw in TEST_CASE_KEYWORDS:
        if kw.lower() in error_lower:
            return "TestCase"

    # Check for specific error types that indicate product issues
    product_errors = [
        "runtimeerror", "assertionerror", "importerror", "modulenotfounderror",
        "typeerror", "valueerror", "keyerror", "indexerror", "attributeerror",
        "notimplementederror", "backend", "kernel", "tensor", "shape mismatch",
        "invalid configuration", "compilation failed",
    ]
    for err in product_errors:
        if err in error_lower:
            return "Product"

    return "Unclassified"


def parse_failed_cases_from_report(log_dir):
    """
    Parse the analysis report to get the list of failed cases.
    Returns list of (case_name, pipeline_name, log_filename)
    """
    report_path = os.path.join(log_dir, "analysis-report.txt")
    if not os.path.exists(report_path):
        # Fallback: scan log files directly
        return scan_logs_directly(log_dir)

    failed_cases = []
    in_failed_list = False

    with open(report_path, "r", encoding="utf-8") as f:
        for line in f:
            strip = line.strip()
            if "[List] All Failed Cases:" in strip:
                in_failed_list = True
                continue
            if in_failed_list:
                if strip.startswith("=") or not strip:
                    break
                # Parse numbered list like " 1. test_npu_xxx.py"
                match = re.match(r"\s*\d+\.\s+(test_[a-zA-Z0-9_]+\.py)", strip)
                if match:
                    case_name = match.group(1)
                    # Find which log file contains this case
                    log_filename = find_log_file_for_case(log_dir, case_name)
                    pipeline = get_pipeline_name(log_filename) if log_filename else "unknown"
                    failed_cases.append((case_name, pipeline, log_filename))

    return failed_cases


def scan_logs_directly(log_dir):
    """
    Fallback: scan all .txt log files to find failed cases.
    """
    failed_cases = []
    seen_cases = set()

    for filename in os.listdir(log_dir):
        if not filename.endswith(".txt"):
            continue
        file_path = os.path.join(log_dir, filename)
        pipeline = get_pipeline_name(filename)

        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except Exception:
            continue

        # Find FAILED markers
        for match in re.finditer(r"FAILED\s+\S*/(test_[a-zA-Z0-9_]+\.py)", content):
            case_name = match.group(1)
            if case_name not in seen_cases:
                seen_cases.add(case_name)
                failed_cases.append((case_name, pipeline, filename))

    return failed_cases


def find_log_file_for_case(log_dir, case_name):
    """
    Find which .txt log file contains the given test case.
    """
    for filename in os.listdir(log_dir):
        if not filename.endswith(".txt"):
            continue
        file_path = os.path.join(log_dir, filename)
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            if case_name in content:
                return filename
        except Exception:
            continue
    return None


def generate_classification_report(log_dir, failed_cases):
    """
    Generate error classification report.
    """
    categories = defaultdict(list)
    case_details = []

    for case_name, pipeline, log_filename in failed_cases:
        if log_filename:
            file_path = os.path.join(log_dir, log_filename)
            error_summary, error_context, classification = find_test_error_in_file(file_path, case_name)
        else:
            error_summary = "Log file not found"
            error_context = ""
            classification = "Unclassified"

        categories[classification].append({
            "case": case_name,
            "pipeline": pipeline,
            "error": error_summary,
            "context": error_context,
        })
        case_details.append({
            "case": case_name,
            "pipeline": pipeline,
            "classification": classification,
            "error": error_summary,
            "context": error_context,
        })

    # Generate report
    report_lines = []
    report_lines.append("=" * 80)
    report_lines.append("[Error Classification Report] NPU Nightly Test Failure Analysis")
    report_lines.append("=" * 80)
    report_lines.append(f"Analysis Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append(f"Log Directory: {log_dir}")
    report_lines.append(f"Total Failed Cases: {len(failed_cases)}")
    report_lines.append("=" * 80)

    # Summary
    report_lines.append("\n[Summary] Failure Category Distribution")
    report_lines.append("-" * 80)
    total = len(failed_cases)
    for cat in ["Product", "TestCase", "Environment", "Unclassified"]:
        count = len(categories[cat])
        pct = (count / total * 100) if total > 0 else 0
        report_lines.append(f"{cat:20s}: {count:3d} ({pct:5.1f}%)")
    report_lines.append("=" * 80)

    # Category details
    for cat in ["Product", "TestCase", "Environment", "Unclassified"]:
        items = categories[cat]
        if not items:
            continue

        report_lines.append(f"\n[{cat} Issues] {len(items)} cases")
        report_lines.append("-" * 80)
        report_lines.append(f"{'Case Name':<45s} | {'Pipeline':<15s} | {'Error Summary'}")
        report_lines.append("-" * 80)
        for item in items:
            case = item["case"][:44]
            pipeline = item["pipeline"][:14]
            error = item["error"][:60]
            report_lines.append(f"{case:<45s} | {pipeline:<15s} | {error}")
        report_lines.append("=" * 80)

    # Detailed error logs
    report_lines.append("\n[Detailed Error Logs]")
    report_lines.append("=" * 80)
    for detail in case_details:
        report_lines.append(f"\n### {detail['case']} ({detail['classification']} Issue)")
        report_lines.append(f"Pipeline: {detail['pipeline']}")
        report_lines.append(f"Error: {detail['error']}")
        report_lines.append("Context:")
        if detail['context']:
            # Limit context to 15 lines
            ctx_lines = detail['context'].split("\n")[:15]
            for line in ctx_lines:
                report_lines.append(f"  {line}")
        else:
            report_lines.append("  (no context available)")
        report_lines.append("-" * 40)

    report_lines.append("\n" + "=" * 80)
    report_lines.append("[END] Classification Complete")
    report_lines.append("=" * 80)

    return "\n".join(report_lines), categories


def generate_zh_report(log_dir, failed_cases, categories):
    """
    Generate Chinese classification report.
    """
    cat_names = {
        "Product": "产品（代码）问题",
        "TestCase": "用例问题",
        "Environment": "环境问题",
        "Unclassified": "未分类",
    }

    report_lines = []
    report_lines.append("=" * 80)
    report_lines.append("[错误分类报告] NPU Nightly 测试失败分析")
    report_lines.append("=" * 80)
    report_lines.append(f"分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append(f"日志目录: {log_dir}")
    report_lines.append(f"总失败用例数: {len(failed_cases)}")
    report_lines.append("=" * 80)

    report_lines.append("\n[汇总] 失败分类分布")
    report_lines.append("-" * 80)
    total = len(failed_cases)
    for cat in ["Product", "TestCase", "Environment", "Unclassified"]:
        count = len(categories[cat])
        pct = (count / total * 100) if total > 0 else 0
        report_lines.append(f"{cat_names[cat]:20s}: {count:3d} ({pct:5.1f}%)")
    report_lines.append("=" * 80)

    for cat in ["Product", "TestCase", "Environment", "Unclassified"]:
        items = categories[cat]
        if not items:
            continue

        report_lines.append(f"\n[{cat_names[cat]}] {len(items)} 个用例")
        report_lines.append("-" * 80)
        report_lines.append(f"{'用例名':<45s} | {'流水线':<15s} | {'错误摘要'}")
        report_lines.append("-" * 80)
        for item in items:
            case = item["case"][:44]
            pipeline = item["pipeline"][:14]
            error = item["error"][:60]
            report_lines.append(f"{case:<45s} | {pipeline:<15s} | {error}")
        report_lines.append("=" * 80)

    return "\n".join(report_lines)


def main(log_dir=None):
    if log_dir is None or log_dir == "":
        print("[ERROR] Please specify the log directory path:")
        print("   python classify-errors.py <log_directory_path>")
        sys.exit(1)

    if not os.path.isdir(log_dir):
        print(f"[ERROR] Directory does not exist: {log_dir}")
        sys.exit(1)

    print(f"[INFO] Analyzing logs in: {log_dir}")

    # Parse failed cases
    failed_cases = parse_failed_cases_from_report(log_dir)
    print(f"[INFO] Found {len(failed_cases)} failed cases")

    if not failed_cases:
        print("[INFO] No failed cases to classify")
        sys.exit(0)

    # Generate reports
    report_en, categories = generate_classification_report(log_dir, failed_cases)
    report_path_en = os.path.join(log_dir, "error-classification-report.txt")
    with open(report_path_en, "w", encoding="utf-8") as f:
        f.write(report_en)
    print(f"[SAVE] English report saved to: {report_path_en}")

    report_zh = generate_zh_report(log_dir, failed_cases, categories)
    report_path_zh = os.path.join(log_dir, "error-classification-report-zh.txt")
    with open(report_path_zh, "w", encoding="utf-8") as f:
        f.write(report_zh)
    print(f"[SAVE] Chinese report saved to: {report_path_zh}")

    # Print summary
    print("\n" + "=" * 60)
    print("[SUMMARY] Error Classification Results")
    print("=" * 60)
    total = len(failed_cases)
    for cat in ["Product", "TestCase", "Environment", "Unclassified"]:
        count = len(categories[cat])
        pct = (count / total * 100) if total > 0 else 0
        print(f"  {cat:15s}: {count:3d} ({pct:5.1f}%)")
    print("=" * 60)
    print("[DONE] Classification complete!")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        main(sys.argv[1])
    else:
        main()
