import os
import re
import sys
from datetime import datetime

# 配置
SUMMARY_PATTERN = re.compile(r"Test Summary: (\d+)/(\d+) passed")
DELIMITER = "============================================================"
TIMESTAMP_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+Z\s*")
TYPE_CARD_PATTERN = re.compile(r'(nightly|full)-(\d+)')
NUMBER_IN_PAREN_PATTERN = re.compile(r'\((\d+)\)')
SKIP_PATTERN = re.compile(r'Skipped (\d+) test\(s\):')
SKIP_CASE_PATTERN = re.compile(r'-\s*(/[^ ]+)\s+\(reason:\s*(.+)\)')

def parse_test_log(file_path):
    passed = 0
    total = 0
    success_cases = []
    failed_cases = []
    skipped_cases = []

    found_summary = False
    record_cases = False
    in_passed = False
    in_failed = False
    in_skipped = False

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except:
        return 0, 0, [], [], []

    for line in lines:
        clean_line = TIMESTAMP_PATTERN.sub("", line).rstrip()
        strip_line = clean_line.strip()

        if "Skipped" in strip_line and "test(s):" in strip_line:
            in_skipped = True
            in_passed = False
            in_failed = False
            continue

        if in_skipped:
            if " Enabled " in strip_line or strip_line.startswith("PASSED") or strip_line.startswith("FAILED") or "test(s) (est total" in strip_line:
                in_skipped = False
                continue

            skip_match = SKIP_CASE_PATTERN.match(strip_line)
            if skip_match:
                case_path = skip_match.group(1)
                reason = skip_match.group(2)
                case_name = os.path.basename(case_path)
                skipped_cases.append((case_name, reason))
            continue

        if not found_summary:
            match = SUMMARY_PATTERN.search(clean_line)
            if match:
                passed = int(match.group(1))
                total = int(match.group(2))
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
                in_passed = True
                in_failed = False
                continue
            if "FAILED:" in clean_line:
                in_failed = True
                in_passed = False
                continue

            if in_passed and strip_line.startswith("/"):
                success_cases.append(os.path.basename(strip_line))

            if in_failed and strip_line.startswith("/"):
                case_path = strip_line.split(" (")[0]
                failed_cases.append(os.path.basename(case_path))

    return passed, total, success_cases, failed_cases, skipped_cases

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
    else:
        return base_name

def find_latest_log_dir():
    """
    Find the latest downloaded log directory under local_data/logs/
    Returns the latest log directory path, or None if not found
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    local_data_logs = os.path.join(script_dir, "..", "..", "..", "local_data", "logs")
    local_data_logs = os.path.normpath(local_data_logs)

    if not os.path.isdir(local_data_logs):
        return None

    date_dirs = []
    for item in os.listdir(local_data_logs):
        item_path = os.path.join(local_data_logs, item)
        if os.path.isdir(item_path):
            try:
                datetime.strptime(item, "%Y-%m-%d")
                date_dirs.append(item_path)
            except ValueError:
                continue

    if not date_dirs:
        return None

    date_dirs.sort(key=lambda x: os.path.getmtime(x), reverse=True)
    latest_date_dir = date_dirs[0]

    log_dirs = []
    for item in os.listdir(latest_date_dir):
        item_path = os.path.join(latest_date_dir, item)
        if os.path.isdir(item_path):
            log_dirs.append(item_path)

    if not log_dirs:
        return None

    log_dirs.sort(key=lambda x: os.path.getmtime(x), reverse=True)
    return log_dirs[0]

def generate_report_en(log_dir):
    """
    Generate English analysis report content
    """
    report_lines = []
    total_all = 0
    pass_all = 0
    skip_all = 0
    all_fails_with_file = []
    all_skipped_with_file = []

    report_lines.append("=" * 80)
    report_lines.append("[Analysis] GitHub Actions Test Log Analysis Report")
    report_lines.append("=" * 80)
    report_lines.append(f"Analysis Directory: {log_dir}")
    report_lines.append(f"Analysis Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append("=" * 80)

    for filename in os.listdir(log_dir):
        file_path = os.path.join(log_dir, filename)
        if not os.path.isfile(file_path) or not filename.endswith(".txt"):
            continue

        p, t, succ, fail, skipped = parse_test_log(file_path)
        if t == 0 and len(skipped) == 0:
            continue

        total_all += t
        pass_all += p
        skip_all += len(skipped)
        for case in fail:
            all_fails_with_file.append((case, "", filename))
        for case, reason in skipped:
            all_skipped_with_file.append((case, reason, filename))

        report_lines.append(f"\n[File] File: {filename}")
        report_lines.append(f"[Result] Result: {p}/{t} passed")
        if len(skipped) > 0:
            report_lines.append(f"[Skip] Skipped: {len(skipped)} case(s)")
        report_lines.append("-" * 60)
        report_lines.append("[OK] PASSED:")
        for case in succ:
            report_lines.append(f"  {case}")
        report_lines.append("\n[FAIL] FAILED:")
        if fail:
            for case in fail:
                report_lines.append(f"  {case}")
        else:
            report_lines.append("  None")
        if skipped:
            report_lines.append("\n[SKIP] SKIPPED:")
            for case, reason in skipped:
                report_lines.append(f"  {case} (reason: {reason})")
        report_lines.append("=" * 80)

    report_lines.append("\n" + "=" * 80)
    report_lines.append("[Table] Failed Cases Table")
    report_lines.append("=" * 80)
    report_lines.append("Case Name\t\tNote\t\tPipeline Name")
    if all_fails_with_file:
        for case, _, filename in all_fails_with_file:
            pipeline_name = get_pipeline_name(filename)
            report_lines.append(f"{case}\t\t\t{pipeline_name}")
    else:
        report_lines.append("[OK] No failed cases")

    unique_skipped = {}
    for case, reason, filename in all_skipped_with_file:
        if case not in unique_skipped:
            unique_skipped[case] = (reason, filename)

    report_lines.append("\n" + "=" * 80)
    report_lines.append("[Table] Skipped Cases Table")
    report_lines.append("=" * 80)
    report_lines.append("Case Name\t\tNote\t\tPipeline Name")
    if unique_skipped:
        for case, (reason, filename) in unique_skipped.items():
            pipeline_name = get_pipeline_name(filename)
            report_lines.append(f"{case}\t{reason}\t{pipeline_name}")
    else:
        report_lines.append("[OK] No skipped cases")

    report_lines.append("\n" + "=" * 80)
    report_lines.append("[Summary] Global Statistics")
    report_lines.append("=" * 80)
    report_lines.append(f"Total Executed Cases: {total_all}")
    report_lines.append(f"Total Passed Cases: {pass_all}")
    report_lines.append(f"Total Failed Cases: {len(all_fails_with_file)}")
    report_lines.append(f"Total Skipped Cases: {len(unique_skipped)} (deduplicated, raw: {skip_all})")
    report_lines.append("\n[List] All Failed Cases:")
    if all_fails_with_file:
        for i, (case, _, _) in enumerate(all_fails_with_file, 1):
            report_lines.append(f"{i:2d}. {case}")
    else:
        report_lines.append("[OK] No failed cases")
    if unique_skipped:
        report_lines.append("\n[List] All Skipped Cases (deduplicated):")
        for i, (case, (reason, filename)) in enumerate(unique_skipped.items(), 1):
            pipeline_name = get_pipeline_name(filename)
            report_lines.append(f"{i:2d}.\t{case}\t{reason}\t{pipeline_name}")
    else:
        report_lines.append("\n[OK] No skipped cases")
    report_lines.append("=" * 80)

    return "\n".join(report_lines), all_fails_with_file, total_all, pass_all

def generate_report_zh(log_dir):
    """
    Generate Chinese analysis report content
    """
    report_lines = []
    total_all = 0
    pass_all = 0
    skip_all = 0
    all_fails_with_file = []
    all_skipped_with_file = []

    report_lines.append("=" * 80)
    report_lines.append("[Analysis] GitHub Actions 测试日志分析报告")
    report_lines.append("=" * 80)
    report_lines.append(f"分析目录: {log_dir}")
    report_lines.append(f"分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append("=" * 80)

    for filename in os.listdir(log_dir):
        file_path = os.path.join(log_dir, filename)
        if not os.path.isfile(file_path) or not filename.endswith(".txt"):
            continue

        p, t, succ, fail, skipped = parse_test_log(file_path)
        if t == 0 and len(skipped) == 0:
            continue

        total_all += t
        pass_all += p
        skip_all += len(skipped)
        for case in fail:
            all_fails_with_file.append((case, "", filename))
        for case, reason in skipped:
            all_skipped_with_file.append((case, reason, filename))

        report_lines.append(f"\n[File] 文件：{filename}")
        report_lines.append(f"[Result] 结果：{p}/{t} passed")
        if len(skipped) > 0:
            report_lines.append(f"[Skip] 跳过：{len(skipped)} 个用例")
        report_lines.append("-" * 60)
        report_lines.append("[OK] PASSED：")
        for case in succ:
            report_lines.append(f"  {case}")
        report_lines.append("\n[FAIL] FAILED：")
        if fail:
            for case in fail:
                report_lines.append(f"  {case}")
        else:
            report_lines.append("  无")
        if skipped:
            report_lines.append("\n[SKIP] SKIPPED：")
            for case, reason in skipped:
                report_lines.append(f"  {case} (reason: {reason})")
        report_lines.append("=" * 80)

    report_lines.append("\n" + "=" * 80)
    report_lines.append("[Table] 失败用例表格")
    report_lines.append("=" * 80)
    report_lines.append("用例名\t\t备注\t\t流水线名")
    if all_fails_with_file:
        for case, _, filename in all_fails_with_file:
            pipeline_name = get_pipeline_name(filename)
            report_lines.append(f"{case}\t\t\t{pipeline_name}")
    else:
        report_lines.append("[OK] 无失败用例")

    unique_skipped = {}
    for case, reason, filename in all_skipped_with_file:
        if case not in unique_skipped:
            unique_skipped[case] = (reason, filename)

    report_lines.append("\n" + "=" * 80)
    report_lines.append("[Table] 跳过用例表格")
    report_lines.append("=" * 80)
    report_lines.append("用例名\t\t备注\t\t流水线名")
    if unique_skipped:
        for case, (reason, filename) in unique_skipped.items():
            pipeline_name = get_pipeline_name(filename)
            report_lines.append(f"{case}\t{reason}\t{pipeline_name}")
    else:
        report_lines.append("[OK] 无跳过用例")

    report_lines.append("\n" + "=" * 80)
    report_lines.append("[Summary] 全局统计结果")
    report_lines.append("=" * 80)
    report_lines.append(f"总执行用例数：{total_all}")
    report_lines.append(f"总成功用例数：{pass_all}")
    report_lines.append(f"总失败用例数：{len(all_fails_with_file)}")
    report_lines.append(f"总跳过用例数：{len(unique_skipped)} (去重后，原始: {skip_all})")
    report_lines.append("\n[List] 全部失败用例清单：")
    if all_fails_with_file:
        for i, (case, _, _) in enumerate(all_fails_with_file, 1):
            report_lines.append(f"{i:2d}. {case}")
    else:
        report_lines.append("[OK] 无失败用例")
    if unique_skipped:
        report_lines.append("\n[List] 全部跳过用例清单（去重后）：")
        for i, (case, (reason, filename)) in enumerate(unique_skipped.items(), 1):
            pipeline_name = get_pipeline_name(filename)
            report_lines.append(f"{i:2d}.\t{case}\t{reason}\t{pipeline_name}")
    else:
        report_lines.append("\n[OK] 无跳过用例")
    report_lines.append("=" * 80)

    return "\n".join(report_lines), all_fails_with_file, total_all, pass_all

def main(log_dir=None):
    if log_dir is None or log_dir == "":
        log_dir = find_latest_log_dir()
        if log_dir is None:
            print("[ERROR] Error: Latest log directory not found")
            print("   Please specify the log directory path:")
            print("   python analyze-log.py <log_directory_path>")
            sys.exit(1)
        print(f"[INFO] Auto-detected latest log directory: {log_dir}")

    if not os.path.isdir(log_dir):
        print(f"[ERROR] Error: Directory does not exist: {log_dir}")
        sys.exit(1)

    # Generate English report
    report_en, all_fails, total, passed = generate_report_en(log_dir)
    report_path_en = os.path.join(log_dir, "analysis-report.txt")
    with open(report_path_en, "w", encoding="utf-8") as f:
        f.write(report_en)
    print(report_en)
    print(f"\n[SAVE] English report saved to: {report_path_en}")

    # Generate Chinese report
    report_zh, _, _, _ = generate_report_zh(log_dir)
    report_path_zh = os.path.join(log_dir, "analysis-report-zh.txt")
    with open(report_path_zh, "w", encoding="utf-8") as f:
        f.write(report_zh)
    print(f"[SAVE] Chinese report saved to: {report_path_zh}")

    print(f"\n[DONE] Analysis complete!")
    print(f"   Total cases: {total}")
    print(f"   Passed: {passed}")
    print(f"   Failed: {len(all_fails)}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        main(sys.argv[1])
    else:
        main()
