# GitHub Actions Failed Tests Report

**Run ID**: 26369251634
**Repository**: sgl-project/sglang
**Date**: 2026-05-25 11:50:55

## Summary Statistics

| Category | Count | Percentage |
|----------|-------|------------|
| **Total Failed Tests** | 59 | 100% |
| **Server Crash** | 56 | 94.9% |
| **Runtime Error** | 2 | 3.4% |
| **Assertion Error** |  | 0% |

## Error Type Analysis

### 1. Server Process Crash (56 tests)

**Root Cause**: Server process exited unexpectedly. Exit code -9 typically indicates:
- **Out of Memory (OOM)** - NPU memory exhaustion
- **SIGKILL** - Process was killed by the system
- **Resource exhaustion** - NPU resources depleted

**Affected Tests**:
- **sampling_backend** (Job: nightly-1-npu-a3 (0), Exit Code: -9)
- **piecewise_graph_prefill** (Job: nightly-1-npu-a3 (0), Exit Code: -9)
- **autoround_moe** (Job: nightly-1-npu-a3 (0), Exit Code: -9)
- **w8a8_quantization** (Job: nightly-1-npu-a3 (0), Exit Code: -9)
- **eagle3** (Job: nightly-1-npu-a3 (0), Exit Code: -9)
- **penalty** (Job: nightly-1-npu-a3 (0), Exit Code: -9)
- **chatglm2_6b** (Job: nightly-1-npu-a3 (0), Exit Code: -9)
- **glm4_9b_chat** (Job: nightly-1-npu-a3 (0), Exit Code: -9)
- **llama_2_7b** (Job: nightly-1-npu-a3 (0), Exit Code: -9)
- **phi_4_multimodal_llm** (Job: nightly-1-npu-a3 (0), Exit Code: 1)
- **radix_cache** (Job: nightly-1-npu-a3 (1), Exit Code: -9)
- **graph_tp1_bf16** (Job: nightly-1-npu-a3 (1), Exit Code: -9)
- **log_level** (Job: nightly-1-npu-a3 (1), Exit Code: -9)
- **autoround_dense** (Job: nightly-1-npu-a3 (1), Exit Code: -9)
- **gptq_moe** (Job: nightly-1-npu-a3 (1), Exit Code: -9)
- **tp1_bf16** (Job: nightly-1-npu-a3 (1), Exit Code: -9)
- **api_abort_request** (Job: nightly-1-npu-a3 (1), Exit Code: -9)
- **matched_stop** (Job: nightly-1-npu-a3 (1), Exit Code: -9)
- **baichuan2_13b_chat** (Job: nightly-1-npu-a3 (1), Exit Code: -9)
- **gemma_3_4b_it_llm** (Job: nightly-1-npu-a3 (1), Exit Code: -9)
- **internlm2_7b** (Job: nightly-1-npu-a3 (1), Exit Code: -9)
- **mistral_7b** (Job: nightly-1-npu-a3 (1), Exit Code: -9)
- **qwen3_0_6b** (Job: nightly-1-npu-a3 (1), Exit Code: -9)
- **gguf** (Job: nightly-1-npu-a3 (1), Exit Code: -9)
- **deepseek_v3_2_exp_w8a8** (Job: nightly-16-npu-a3 (0), Exit Code: -9)
- **qwen3_vl_235b_a22b_instruct** (Job: nightly-16-npu-a3 (0), Exit Code: -9)
- **qwen3_coder_480b_a35b** (Job: nightly-16-npu-a3 (1), Exit Code: -9)
- **deepep_auto_qwen3_480b** (Job: nightly-16-npu-a3 (1), Exit Code: -9)
- **offload_modes** (Job: nightly-2-npu-a3 (0), Exit Code: -9)
- **gguf_moe** (Job: nightly-2-npu-a3 (0), Exit Code: -9)
- **graph_tp2_bf16** (Job: nightly-2-npu-a3 (0), Exit Code: -9)
- **mla_fia_w8a8int8** (Job: nightly-2-npu-a3 (0), Exit Code: -9)
- **tp2_bf16** (Job: nightly-2-npu-a3 (0), Exit Code: -9)
- **tp2_fia_bf16** (Job: nightly-2-npu-a3 (0), Exit Code: -9)
- **openai_server_ignore_eos** (Job: nightly-2-npu-a3 (0), Exit Code: -9)
- **qwen3_30b** (Job: nightly-2-npu-a3 (0), Exit Code: -9)
- **qwq_32b_w8a8** (Job: nightly-2-npu-a3 (0), Exit Code: -9)
- **memory_consumption** (Job: nightly-2-npu-a3 (0), Exit Code: -9)
- **hicache_mla** (Job: nightly-4-npu-a3 (0), Exit Code: -9)
- **w4a4_quantization** (Job: nightly-4-npu-a3 (0), Exit Code: -9)
- **mla_w8a8int8** (Job: nightly-4-npu-a3 (0), Exit Code: -9)
- **tp4_bf16** (Job: nightly-4-npu-a3 (0), Exit Code: -9)
- **qwen3_32b** (Job: nightly-4-npu-a3 (0), Exit Code: -9)
- **gemma_3_4b_it** (Job: nightly-4-npu-a3 (0), Exit Code: -9)
- **janus_pro_1b** (Job: nightly-4-npu-a3 (0), Exit Code: -9)
- **janus_pro_7b** (Job: nightly-4-npu-a3 (0), Exit Code: -9)
- **mimo_vl_7b_rl** (Job: nightly-4-npu-a3 (0), Exit Code: -9)
- **minicpm_v_2_6** (Job: nightly-4-npu-a3 (0), Exit Code: -9)
- **mistral_small_3_1_24b_instruct_2503** (Job: nightly-4-npu-a3 (0), Exit Code: -9)
- **phi4_multimodal_instruct** (Job: nightly-4-npu-a3 (0), Exit Code: 1)
- **qwen2_5_vl_3b_instruct** (Job: nightly-4-npu-a3 (0), Exit Code: -9)
- **qwen3_vl_30b_a3b_instruct** (Job: nightly-4-npu-a3 (0), Exit Code: -9)
- **qwen3_vl_8b_instruct** (Job: nightly-4-npu-a3 (0), Exit Code: -9)
- **dbrx_instruct** (Job: nightly-8-npu-a3 (0), Exit Code: 1)
- **glm_4_5v** (Job: nightly-8-npu-a3 (0), Exit Code: -9)
- **qwen2_5_vl_72b_instruct** (Job: nightly-8-npu-a3 (0), Exit Code: -9)
### 2. Runtime Error (2 tests)

**Root Cause**: Process tree cleanup failure or other runtime issues.

**Affected Tests**:
- **original_logprobs** (Job: nightly-1-npu-a3 (0))
  - Error: kill_process_tree: 98 process(es) not reaped within 60s after SIGKILL; pids=[23483, 23495, 25076, 23465, 25446, 25054, 23485, 25026, 25365, 25046, 25348, 23497, 25334, 25056, 25044, 25357, 25361, 25346, 25070, 23499, 24950, 25048, 25336, 25324, 23479, 25363, 25030, 25367, 23451, 23491, 25450, 25350, 23471, 25432, 23481, 25024, 23469, 25440, 25352, 25022, 25242, 25072, 23437, 25042, 25062, 23473, 23445, 23455, 25034, 25052, 25434, 25340, 25016, 25344, 23487, 23447, 25078, 25066, 25036, 23467, 25332, 25436, 25444, 23439, 23489, 23459, 25064, 23449, 25068, 25028, 23457, 23477, 25438, 25020, 25448, 23441, 25359, 25018, 25038, 23461, 25338, 25326, 23443, 25058, 25040, 25330, 25442, 25354, 25050, 25060, 25328, 25074, 25032, 23493, 23453, 23475, 23463, 25342]
- **bge_reranker_v2_m3** (Job: nightly-1-npu-a3 (0))
  - Error: kill_process_tree: 66 process(es) not reaped within 60s after SIGKILL; pids=[45208, 44924, 44906, 45226, 45200, 44914, 44878, 44888, 45244, 44910, 45230, 45246, 44926, 45212, 44936, 44900, 45186, 45224, 45204, 44896, 44912, 44876, 44886, 45198, 45228, 45216, 44932, 44930, 45190, 44898, 45218, 45234, 45242, 45202, 44916, 44880, 44890, 45192, 45206, 45220, 44938, 44908, 44882, 45194, 45210, 44934, 45099, 45236, 44894, 45232, 44884, 45184, 45214, 44920, 45240, 44918, 44810, 44892, 44902, 45222, 45238, 45188, 44928, 44922, 45196, 44904]
### 3. Assertion Error ( tests)

**Root Cause**: Assertion failures during test execution.

**Affected Tests**:
- **minimax_m2** (Job: nightly-8-npu-a3 (0))
  - Error: Test failed for /root/.cache/modelscope/hub/models/cyankiwi/MiniMax-M2-BF16: Server failed to start within the timeout period
## Failed Tests by Job

### nightly-1-npu-a3 (0) (12 failures)

| Test Name | Error Type | Exit Code |
|-----------|------------|-----------|
| sampling_backend | ServerCrash | -9 |
| piecewise_graph_prefill | ServerCrash | -9 |
| original_logprobs | RuntimeError |  |
| autoround_moe | ServerCrash | -9 |
| w8a8_quantization | ServerCrash | -9 |
| eagle3 | ServerCrash | -9 |
| penalty | ServerCrash | -9 |
| chatglm2_6b | ServerCrash | -9 |
| glm4_9b_chat | ServerCrash | -9 |
| llama_2_7b | ServerCrash | -9 |
| phi_4_multimodal_llm | ServerCrash | 1 |
| bge_reranker_v2_m3 | RuntimeError |  |

### nightly-1-npu-a3 (1) (14 failures)

| Test Name | Error Type | Exit Code |
|-----------|------------|-----------|
| radix_cache | ServerCrash | -9 |
| graph_tp1_bf16 | ServerCrash | -9 |
| log_level | ServerCrash | -9 |
| autoround_dense | ServerCrash | -9 |
| gptq_moe | ServerCrash | -9 |
| tp1_bf16 | ServerCrash | -9 |
| api_abort_request | ServerCrash | -9 |
| matched_stop | ServerCrash | -9 |
| baichuan2_13b_chat | ServerCrash | -9 |
| gemma_3_4b_it_llm | ServerCrash | -9 |
| internlm2_7b | ServerCrash | -9 |
| mistral_7b | ServerCrash | -9 |
| qwen3_0_6b | ServerCrash | -9 |
| gguf | ServerCrash | -9 |

### nightly-16-npu-a3 (0) (2 failures)

| Test Name | Error Type | Exit Code |
|-----------|------------|-----------|
| deepseek_v3_2_exp_w8a8 | ServerCrash | -9 |
| qwen3_vl_235b_a22b_instruct | ServerCrash | -9 |

### nightly-16-npu-a3 (1) (2 failures)

| Test Name | Error Type | Exit Code |
|-----------|------------|-----------|
| qwen3_coder_480b_a35b | ServerCrash | -9 |
| deepep_auto_qwen3_480b | ServerCrash | -9 |

### nightly-2-npu-a3 (0) (10 failures)

| Test Name | Error Type | Exit Code |
|-----------|------------|-----------|
| offload_modes | ServerCrash | -9 |
| gguf_moe | ServerCrash | -9 |
| graph_tp2_bf16 | ServerCrash | -9 |
| mla_fia_w8a8int8 | ServerCrash | -9 |
| tp2_bf16 | ServerCrash | -9 |
| tp2_fia_bf16 | ServerCrash | -9 |
| openai_server_ignore_eos | ServerCrash | -9 |
| qwen3_30b | ServerCrash | -9 |
| qwq_32b_w8a8 | ServerCrash | -9 |
| memory_consumption | ServerCrash | -9 |

### nightly-4-npu-a3 (0) (15 failures)

| Test Name | Error Type | Exit Code |
|-----------|------------|-----------|
| hicache_mla | ServerCrash | -9 |
| w4a4_quantization | ServerCrash | -9 |
| mla_w8a8int8 | ServerCrash | -9 |
| tp4_bf16 | ServerCrash | -9 |
| qwen3_32b | ServerCrash | -9 |
| gemma_3_4b_it | ServerCrash | -9 |
| janus_pro_1b | ServerCrash | -9 |
| janus_pro_7b | ServerCrash | -9 |
| mimo_vl_7b_rl | ServerCrash | -9 |
| minicpm_v_2_6 | ServerCrash | -9 |
| mistral_small_3_1_24b_instruct_2503 | ServerCrash | -9 |
| phi4_multimodal_instruct | ServerCrash | 1 |
| qwen2_5_vl_3b_instruct | ServerCrash | -9 |
| qwen3_vl_30b_a3b_instruct | ServerCrash | -9 |
| qwen3_vl_8b_instruct | ServerCrash | -9 |

### nightly-8-npu-a3 (0) (4 failures)

| Test Name | Error Type | Exit Code |
|-----------|------------|-----------|
| dbrx_instruct | ServerCrash | 1 |
| minimax_m2 | AssertionError |  |
| glm_4_5v | ServerCrash | -9 |
| qwen2_5_vl_72b_instruct | ServerCrash | -9 |

## Recommended Fixes

1. **Investigate NPU Resource Usage**: The high rate of Server Crash (exit code -9) suggests NPU memory exhaustion. Consider:
   - Reducing concurrent test execution
   - Increasing memory allocation per test
   - Adding memory monitoring and cleanup between tests

2. **Process Cleanup**: Fix the process tree cleanup issue in 	est_npu_bge_reranker_v2_m3.py - 66 processes were not properly reaped.

3. **Add Error Handling**: Implement better error handling and graceful shutdown for server processes.

4. **Increase Timeouts**: Consider increasing process termination timeout from 60s to allow proper cleanup.

---

*Report generated automatically from GitHub Actions logs*