#echo performance | tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor
#sysctl -w vm.swappiness=0
#sysctl -w kernel.numa_balancing=0
#sysctl -w kernel.sched_migration_cost_ns=50000
export SGLANG_SET_CPU_AFFINITY=1
unset ASCEND_LAUNCH_BLOCKING

#source /usr/local/Ascend/ascend-toolkit/set_env.sh
#source /usr/local/Ascend/nnal/atb/set_env.sh
#source /usr/local/Ascend/ascend-toolkit/latest/opp/vendors/customize/bin/set_env.bash
#export ASCEND_HOME_PATH=/usr/local/Ascend/ascend-toolkit/latest
#export PYTHONPATH=/data/dzc/code/cp/sglang/python:$PYTHONPATH
#export PYTHONPATH=/data/dzc/b022/scp/sglang-npu-nn-B022/python:$PYTHONPATH
export PYTORCH_NPU_ALLOC_CONF=expandable_segments:True
export STREAMS_PER_DEVICE=32

export SGLANG_DEEPEP_NUM_MAX_DISPATCH_TOKENS_PER_RANK=16
export HCCL_BUFFSIZE=1024
export HAS_INDEX_K=1
export SGLANG_DEEPEP_BF16_DISPATCH=0
export SGLANG_NPU_USE_MLAPO=0
export SGLANG_NPU_USE_MLAPROLOG=0
export USE_MULTI_STREAM=1
export ENABLE_FUSED_MOE=1
export HCCL_OP_EXPANSION_MODE=AIV
export TASK_QUEUE_ENABLE=0
export DEEP_NORMAL_MODE_USE_INT8_QUANT=1
# MTP
#export SGLANG_EBABLE_OVERLAP_PLAN_STREAM=1
#export SGLANG_ENABLE_SPEC_V2=1


D_HOST_IP=('192.168.0.102' '192.168.0.184')
export ASCEND_MF_STORE_URL="tcp://192.168.0.60:24667"
export HCCL_SOCKET_IFNAME="enp23s0f3"
export GLOO_SOCKET_IFNAME="enp23s0f3"

 python -m sglang.launch_server \
	--model-path /data/ascend-ci-share-pkking-sglang/modelscope/hub/models/vllm-ascend/DeepSeek-R1-0528-W8A8 \
	--tp 16 \
	--moe-dense-tp-size 1 \
	--enable-dp-attention \
	--enable-dp-lm-head \
	--trust-remote-code \
	--attention-backend ascend \
	--device npu \
	--watchdog-timeout 9000 \
	--host 192.168.0.184 \
	--port 30000 \
	--mem-fraction-static 0.8 \
	--context-length 68000 \
	--disable-radix-cache \
	--chunked-prefill-size 262144 \
	--max-prefill-tokens 68000 \
	--max-running-requests 128 \
	--cuda-graph-max-bs 32 \
	--moe-a2a-backend deepep \
	--deepep-mode low_latency \
	--quantization modelslim \
	--disaggregation-transfer-backend ascend \
	--disaggregation-mode decode \
	--prefill-round-robin-balance \
	--load-balance-method round_robin \
