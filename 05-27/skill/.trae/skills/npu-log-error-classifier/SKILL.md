---
name: "npu-log-error-classifier"
description: "Extracts error details from failed test cases in NPU nightly logs and classifies them into product bugs, test case issues, or environment problems. Invoke when user wants to understand WHY tests failed, classify failure root causes, or analyze error patterns from NPU CI logs."
---

# NPU Log Error Classifier

This skill extracts detailed error messages from failed test cases in NPU nightly test logs, then classifies each failure into one of three categories:

1. **Product (Code) Issue** — Bugs in the actual product code
2. **Test Case Issue** — Problems with the test itself (wrong parameters, outdated assertions, etc.)
3. **Environment Issue** — Infrastructure/hardware problems (runner failure, network timeout, resource shortage, etc.)

## When to Invoke

- User asks "为什么这些用例失败了"
- User wants to understand the root cause of test failures
- User asks to classify or categorize failures
- User wants to extract error details from logs
- User says something like "分析失败原因" or "看看这些错误是什么"

## Workflow Steps

### Phase 1: Extract Error Details

For each failed test case found in the log analysis report, locate the detailed error in the corresponding `.txt` log file.

#### Error Extraction Rules

Search for error patterns near the test case name in the log file:

```python
# Key patterns to search for near a failed test case:
ERROR_PATTERNS = [
    r"(RuntimeError|AssertionError|ImportError|ModuleNotFoundError|TypeError|ValueError|KeyError|IndexError):\s*(.+)",
    r"FAILED\s+\S*test_npu_\S+\s+-\s+(.+)",
    r"Error:\s*(.+)",
    r"exit code\s+(\d+)",
    r"No backend type associated with device type",
    r"torch\.compile.*?error",
    r"CUDA|NPU.*?error",
    r"Connection.*?timeout",
    r"ResourceExhaustedError",
    r"OOM|out of memory",
    r"Device.*?not available",
    r"SSH|runner.*?failed",
    r"docker.*?error",
    r"pytest.*?error",
]
```

#### Context Window

For each failed case, extract **up to 20 lines of context** before and after the error occurrence to capture the full stack trace.

### Phase 2: Classify Errors

Classify each extracted error into one of three categories:

#### Category 1: Product (Code) Issue

**Indicators:**
- `RuntimeError` related to model inference, tensor operations, or kernels
- `AssertionError` in model output validation
- `ImportError` / `ModuleNotFoundError` for product modules
- `TypeError` / `ValueError` in API usage
- `KeyError` / `IndexError` in data processing
- Backend errors like "No backend type associated with device type"
- Compilation errors (`torch.compile` failures)
- Numerical errors (NaN, Inf, precision issues)

**Examples:**
```
RuntimeError: CUDA error: invalid configuration argument
AssertionError: assert output.shape == expected_shape
ImportError: cannot import name 'xxx' from 'sglang'
```

#### Category 2: Test Case Issue

**Indicators:**
- Wrong test parameters or configurations
- Outdated test assertions
- Missing test dependencies (test-only packages)
- Incorrect test data paths
- Flaky test patterns (random failures)
- Test timeout due to overly strict thresholds
- Mock/patch failures

**Examples:**
```
FileNotFoundError: test_data/model_config.json not found
AssertionError: expected 0.95 but got 0.94 (tolerance too strict)
pytest.PytestCollectionWarning: cannot collect test class 'TestXXX'
```

#### Category 3: Environment Issue

**Indicators:**
- Runner/SSH connection failures
- Docker/container errors
- Network timeouts during model download
- Out of memory (OOM) due to insufficient hardware
- Device not available / hardware not found
- Permission denied on shared resources
- Git clone / artifact download failures
- Runner crashed or was preempted

**Examples:**
```
ConnectionError: Failed to connect to runner
RuntimeError: NPU device not available
OOM when allocating tensor of shape [xxx]
docker: Error response from daemon: container failed
```

### Phase 3: Generate Classification Report

Generate a structured report with the following sections:

```
================================================================================
[Error Classification Report] NPU Nightly Test Failure Analysis
================================================================================
Run: #{run_number} | Date: {date} | Total Failed: {count}
================================================================================

[Summary] Failure Category Distribution
--------------------------------------------------------------------------------
Product (Code) Issues:  {count} ({percentage}%)
Test Case Issues:       {count} ({percentage}%)
Environment Issues:     {count} ({percentage}%)
Unclassified:           {count} ({percentage}%)
================================================================================

[Product Issues] {count} cases
--------------------------------------------------------------------------------
Case Name                    | Pipeline      | Error Summary
-----------------------------|---------------|----------------------------------
test_npu_xxx.py              | nightly-2-(0) | RuntimeError: invalid config...
test_npu_yyy.py              | nightly-4-(0) | AssertionError: shape mismatch...
...

[Test Case Issues] {count} cases
--------------------------------------------------------------------------------
Case Name                    | Pipeline      | Error Summary
-----------------------------|---------------|----------------------------------
test_npu_zzz.py              | nightly-1-(0) | FileNotFoundError: missing data...
...

[Environment Issues] {count} cases
--------------------------------------------------------------------------------
Case Name                    | Pipeline      | Error Summary
-----------------------------|---------------|----------------------------------
test_npu_aaa.py              | nightly-8-(0) | OOM: insufficient memory...
...

[Unclassified] {count} cases
--------------------------------------------------------------------------------
Case Name                    | Pipeline      | Raw Error Snippet
-----------------------------|---------------|----------------------------------
...

[Detailed Error Logs]
--------------------------------------------------------------------------------
### test_npu_xxx.py (Product Issue)
Pipeline: nightly-2-(0)
Error:
<full error context (up to 20 lines)>

### test_npu_yyy.py (Product Issue)
...
================================================================================
```

## Implementation Approach

### Option A: Extend Existing Script

Modify `git/log/analyze/analyze-log.py` to add error extraction and classification:

1. After parsing failed cases, open each log file again
2. Search for the test case name and extract surrounding error context
3. Apply classification rules
4. Append classification section to existing reports

### Option B: Create Standalone Classifier

Create a new script `git/log/analyze/classify-errors.py` that:

1. Takes the log directory as input
2. Reads the existing `analysis-report.txt` to get failed case list
3. Extracts error details from raw `.txt` log files
4. Classifies each error
5. Generates `error-classification-report.txt` and `error-classification-report-zh.txt`

## Classification Heuristics

Use keyword matching with priority:

```python
ENVIRONMENT_KEYWORDS = [
    "OOM", "out of memory", "ResourceExhausted",
    "device not available", "NPU not found", "CUDA error",
    "runner", "SSH", "connection", "timeout", "docker",
    "permission denied", "No space left", "runner disconnected",
    "failed to start container", "artifact download failed"
]

TEST_CASE_KEYWORDS = [
    "FileNotFoundError", "test data", "fixture",
    "cannot collect test class", "pytest",
    "tolerance", "threshold too strict",
    "mock", "patch", "wrong parameter"
]

# Default to Product Issue if neither environment nor test case
```

## Required Parameters

- `log_dir` — Path to extracted log directory (containing `.txt` files)

## Output Files

| File | Description |
|------|-------------|
| `error-classification-report.txt` | English classification report |
| `error-classification-report-zh.txt` | Chinese classification report |

## Notes

- Classification is heuristic-based and may require manual review
- Some errors may span multiple categories (e.g., OOM could be environment OR product memory leak)
- When in doubt, mark as "Unclassified" and include raw error for human review
- The classification accuracy improves with more domain-specific keyword tuning
