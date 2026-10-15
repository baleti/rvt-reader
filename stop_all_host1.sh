#!/bin/sh
# stop every rvt-research job on this host (never touches VMs)
for pat in run_fid_full restart_fid chain_pout2 start_pout2 start_pout run_pool eval_params_all fidelity_full fidelity_eval run_prewarm rvt_cache_get rvt2text.py run_geomtest; do
  for p in $(pgrep -f "$pat"); do [ "$p" != "$$" ] && kill $p 2>/dev/null; done
done
sleep 2
echo stopped
