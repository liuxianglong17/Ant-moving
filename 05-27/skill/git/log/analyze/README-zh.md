# GitHub Actions 日志分析工具

基于 Python 实现的 GitHub Actions 工作流运行日志分析工具，生成测试结果报告、失败用例表格和跳过用例表格。

## 功能特性

- **自动日志解析**：从日志文件中解析测试摘要、通过/失败/跳过的用例
- **流水线名称识别**：从文件名中提取流水线名称（如 `nightly-8-npu-a3`）
- **失败用例表格**：列出所有失败用例及其所属流水线
- **跳过用例表格**：列出所有跳过用例及其原因和所属流水线（去重）
- **全局统计**：总执行、通过、失败、跳过用例数量
- **自动目录检测**：自动查找最新下载的日志目录

## 目录结构

```
git/log/analyze/
├── analyze-log.py         # 主脚本
├── README.md              # 英文文档
└── README-zh.md           # 中文文档
```

## 使用方法

### 分析指定日志目录

```powershell
python "git/log/analyze/analyze-log.py" "d:\personal_code\My-agent-assistant\local_data\logs\2026-05-26\sgl-project-sglang-26414786878"
```

### 自动检测最新日志目录

```powershell
cd d:\personal_code\My-agent-assistant
python "git/log/analyze/analyze-log.py"
```

### 参数说明

| 参数   | 类型   | 必填 | 默认值 | 说明               |
|--------|--------|------|--------|--------------------|
| LogDir | string | 否   | 自动   | 要分析的日志目录路径 |

## 输出内容

脚本在指定的日志目录中同时生成双语报告：

| 文件名 | 语言 | 说明 |
|--------|------|------|
| `analysis-report.txt` | 英文 | 英文版分析报告 |
| `analysis-report-zh.txt` | 中文 | 中文版分析报告 |

两份报告内容一致，包含：

1. **逐文件分析**：每个 job 日志文件的测试摘要
2. **失败用例表格**：用例名、备注、流水线名
3. **跳过用例表格**：用例名、原因、流水线名（去重）
4. **全局统计**：总用例数、通过数、失败数、跳过数
5. **失败用例清单**：带编号的全部失败用例列表
6. **跳过用例清单**：带编号的全部跳过用例列表（去重后）

## 输出示例

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

## 注意事项

- 脚本分析指定目录下的所有 `.txt` 文件
- 没有测试摘要或跳过用例的文件会被忽略
- 跳过用例全局去重（相同用例名只保留一次）
- 流水线名称从匹配 `(nightly|full)-(\d+)` 模式的文件名中提取
- 同时输出英文 (`analysis-report.txt`) 和中文 (`analysis-report-zh.txt`) 两份报告
- 两份报告内容一致，仅语言不同
