echo performance | tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor
sysctl -w vm.swappiness=0
sysctl -w kernel.numa_balancing=0
sysctl -w kernel.sched_migration_cost_ns=50000
# 绑核
export SGLANG_SET_CPU_AFFINITY=1
unset https_proxy
unset http_proxy
unset HTTPS_PROXY
unset HTTP_PROXY
unset ASCEND_LAUNCH_BLOCKING

source /usr/local/Ascend/ascend-toolkit/set_env.sh
source /usr/local/Ascend/nnal/atb/set_env.sh

export STREAMS_PER_DEVICE=32
# 网卡
export HCCL_SOCKET_IFNAME=lo
export GLOO_SOCKET_IFNAME=lo
# model path

# 最新w4a8权重-mlp未量化
MODEL_PATH=/home/weights/GLM-5-w4a8-new-fix


P_IP=('61.47.19.75' '61.47.19.70')
P_MASTER="${P_IP[0]}:4567"
export SGLANG_DISAGGREGATION_BOOTSTRAP_TIMEOUT=600

# mtp环境变量
export SGLANG_ENABLE_SPEC_V2=1
export SGLANG_ENABLE_OVERLAP_PLAN_STREAM=1

LOCAL_HOST1=`hostname -I|awk -F " " '{print$1}'`
LOCAL_HOST2=`hostname -I|awk -F " " '{print$2}'`

echo "${LOCAL_HOST1}"
echo "${LOCAL_HOST2}"

export SGLANG_DEEPEP_NUM_MAX_DISPATCH_TOKENS_PER_RANK=16
export DEEP_NORMAL_MODE_USE_INT8_QUANT=1
export HCCL_BUFFSIZE=3000
python3 -m sglang.launch_server \
        --model-path $MODEL_PATH \
        --attention-backend ascend \
        --device npu \
        --tp-size 16 --nnodes 1 --node-rank 0 \
        --chunked-prefill-size -1 --max-prefill-tokens 65536 \
        --trust-remote-code \
        --host 127.0.0.1 \
        --mem-fraction-static 0.6 \
        --port 8001 \
        --served-model-name glm-5 \
        --cuda-graph-max-bs 16 \
        --quantization modelslim \
  --speculative-draft-model-quantization unquant \
        --moe-a2a-backend deepep --deepep-mode auto \
        --speculative-algorithm NEXTN \
        --speculative-num-steps 3 \
        --speculative-eagle-topk 1 \
        --speculative-num-draft-tokens 4 \
        --dp-size 4 --enable-dp-attention
