# GitHub Actions Log Analyzer

A Python-based tool to analyze GitHub Actions workflow run logs, generating test result reports, failed cases table, and skipped cases table.

## Features

- **Automatic log parsing**: Parses test summary, passed/failed/skipped cases from log files
- **Pipeline name detection**: Extracts pipeline names from filenames (e.g., `nightly-8-npu-a3`)
- **Failed cases table**: Lists all failed cases with pipeline names
- **Skipped cases table**: Lists all skipped cases with reasons and pipeline names (deduplicated)
- **Global statistics**: Total executed, passed, failed, and skipped case counts
- **Auto directory detection**: Automatically finds the latest downloaded log directory

## Directory Structure

```
git/log/analyze/
├── analyze-log.py         # Main script
├── README.md              # English documentation
└── README-zh.md           # Chinese documentation
```

## Usage

### Analyze specified log directory

```powershell
python "git/log/analyze/analyze-log.py" "d:\personal_code\My-agent-assistant\local_data\logs\2026-05-26\sgl-project-sglang-26414786878"
```

### Auto-detect latest log directory

```powershell
cd d:\personal_code\My-agent-assistant
python "git/log/analyze/analyze-log.py"
```

### Parameters

| Parameter | Type   | Required | Default | Description                          |
|-----------|--------|----------|---------|--------------------------------------|
| LogDir    | string | No       | Auto    | Path to the log directory to analyze |

## Output

The script generates bilingual reports in the specified log directory:

| File Name | Language | Description |
|-----------|----------|-------------|
| `analysis-report.txt` | English | English analysis report |
| `analysis-report-zh.txt` | Chinese | Chinese analysis report |

Both reports contain the same content:

1. **Per-file analysis**: Test summary for each job log file
2. **Failed cases table**: Case name, note, pipeline name
3. **Skipped cases table**: Case name, reason, pipeline name (deduplicated)
4. **Global statistics**: Total cases, passed, failed, skipped counts
5. **Failed cases list**: Numbered list of all failed cases
6. **Skipped cases list**: Numbered list of all skipped cases (deduplicated)

## Example Output

```
================================================================================
[Analysis] GitHub Actions Test Log Analysis Report
================================================================================
Analysis Directory: d:\personal_code\My-agent-assistant\local_data\logs\2026-05-26\sgl-project-sglang-26414786878
Analysis Time: 2026-05-26 20:15:30
================================================================================

[File] File: nightly-8-npu-a3 (0).txt
[Result] Result: 45/50 passed
[Skip] Skipped: 2 case(s)
------------------------------------------------------------
[OK] PASSED:
  test_case_a.py
  test_case_b.py

[FAIL] FAILED:
  test_case_c.py
  test_case_d.py
  test_case_e.py

[SKIP] SKIPPED:
  test_case_f.py (reason: hardware not available)
  test_case_g.py (reason: unstable)
================================================================================

================================================================================
[Table] Failed Cases Table
================================================================================
Case Name		Note		Pipeline Name
test_case_c.py			nightly-8-(0)
test_case_d.py			nightly-8-(0)
test_case_e.py			nightly-8-(0)

================================================================================
[Table] Skipped Cases Table
================================================================================
Case Name		Note		Pipeline Name
test_case_f.py	hardware not available	nightly-8-(0)
test_case_g.py	unstable	nightly-8-(0)

================================================================================
[Summary] Global Statistics
================================================================================
Total Executed Cases: 50
Total Passed Cases: 45
Total Failed Cases: 3
Total Skipped Cases: 2 (deduplicated, raw: 2)

[List] All Failed Cases:
 1. test_case_c.py
 2. test_case_d.py
 3. test_case_e.py

[List] All Skipped Cases (deduplicated):
 1.	test_case_f.py	hardware not available	nightly-8-(0)
 2.	test_case_g.py	unstable	nightly-8-(0)
================================================================================
```

## Notes

- The script analyzes all `.txt` files in the specified directory
- Files without test summary or skipped cases are ignored
- Skipped cases are deduplicated globally (same case name appears only once)
- Pipeline names are extracted from filenames matching pattern `(nightly|full)-(\d+)`
- Both English (`analysis-report.txt`) and Chinese (`analysis-report-zh.txt`) reports are generated
- Both reports contain identical content, only the language differs
