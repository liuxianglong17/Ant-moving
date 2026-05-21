#echo performance | tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor
#sysctl -w vm.swappiness=0
#sysctl -w kernel.numa_balancing=0
#sysctl -w kernel.sched_migration_cost_ns=50000
export SGLANG_SET_CPU_AFFINITY=1
unset ASCEND_LAUNCH_BLOCKING

#source /usr/local/Ascend/ascend-toolkit/set_env.sh
#source /usr/local/Ascend/nnal/atb/set_env.sh
#source /usr/local/Ascend/ascend-toolkit/latest/opp/vendors/customize/bin/set_env.bash
#export LD_LIBRARY_PATH=/usr/local/Ascend/ascend-toolkit/latest/opp/vendors/customize/op_api/lib/:${LD_LIBRARY_PATH}
#export ASCEND_HOME_PATH=/usr/local/Ascend/ascend-toolkit/latest
#export PYTHONPATH=/data/dzc/b022/scp/sglang-npu-nn-B022/python:$PYTHONPATH

export PYTORCH_NPU_ALLOC_CONF=expandable_segments:True
export STREAMS_PER_DEVICE=32

export SGLANG_DEEPEP_NUM_MAX_DISPATCH_TOKENS_PER_RANK=16
export HCCL_BUFFSIZE=2800
#export HCCL_BUFFSIZE=3200
export HAS_INDEX_K=1
export SGLANG_DEEPEP_BF16_DISPATCH=0
export SGLANG_NPU_USE_MLAPO=0
export SGLANG_USE_AG_AFTER_QLORA=0
export USE_MULTI_STREAM=1
export ENABLE_MOE_NZ=1
export PROFILING_MODE=dynamic
export HCCL_OP_EXPANSION_MODE=AIV
# MTP
#export SGLANG_EBABLE_OVERLAP_PLAN_STREAM=1
#export SGLANG_ENABLE_SPEC_V2=1


export ASCEND_MF_STORE_URL="tcp://192.168.0.60:24667"
export HCCL_SOCKET_IFNAME="enp23s0f3"
export GLOO_SOCKET_IFNAME="enp23s0f3"

 python -m sglang.launch_server \
	--model-path /data/ascend-ci-share-pkking-sglang/modelscope/hub/models/vllm-ascend/DeepSeek-R1-0528-W8A8 \
	--tp 16 \
	--trust-remote-code \
	--attention-backend ascend \
	--device npu \
	--watchdog-timeout 9000 \
	--host 192.168.0.81 \
 	--port 30000 \
	--mem-fraction-static 0.8 \
	--max-total-tokens 68000 \
	--context-length 68000 \
	--disable-radix-cache \
	--chunked-prefill-size 327680 \
	--max-prefill-tokens 68000 \
	--max-running-requests 16 \
	--moe-a2a-backend deepep \
	--deepep-mode auto \
	--quantization modelslim \
	--disaggregation-transfer-backend ascend \
	--disaggregation-mode prefill \
	--disable-cuda-graph \
	--disaggregation-bootstrap-port 8999
