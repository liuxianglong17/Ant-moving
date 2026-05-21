unset ASCEND_LAUNCH_BLOCKING
#source /usr/local/Ascend/ascend-toolkit/set_env.sh
#source /usr/local/Ascend/nnal/atb/set_env.sh
#source /usr/local/Ascend/ascend-toolkit/latest/opp/vendors/customize/bin/set_env.bash
#export ASCEND_HOME_PATH=/usr/local/Ascend/ascend-toolkit/latest
export ASCEND_MF_STORE_URL="tcp://192.168.0.60:24667"
export HCCL_SOCKET_IFNAME="enp23s0f3"
export GLOO_SOCKET_IFNAME="enp23s0f3"

 python -m sglang_router.launch_router \
	--decode http://192.168.0.184:30000 \
	--prefill http://192.168.0.60:30000 8997 \
       	--prefill http://192.168.0.77:30000 8998 \
	--prefill http://192.168.0.81:30000 8999 \
	--pd-disaggregation \
	--prefill-policy bucket \
	--balance-rel-threshold 1.0001 \
	--balance-abs-threshold 32 \
	--bucket-adjust-interval-secs 5 \
	--host 192.168.0.60 \
	--port 6699 

 # 4294967296
