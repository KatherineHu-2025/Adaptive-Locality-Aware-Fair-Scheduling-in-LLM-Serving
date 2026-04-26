# LooGLE Starvation V4 Analysis (Merged 6-Policy View)

Date: 2026-04-26
Merged inputs:
- results/modal_grid_20260426_000325
- results/modal_grid_20260426_005716
Merged dataset:
- results/modal_grid_20260426_v4_merged
Plots folder:
- docs/plots/loogle_starvation_v4

## Commands Used

Baseline run:
set AIMD_MULT_FACTOR=0.65 && python benchmark_modal_service_loogle_prefix_grid.py --policies adaptive_dlpm,fcfs,lpm,dlpm --rates 5 --ks 1.0 --request-counts 1800 --max-concurrency 8 --loogle-prefix-dominant-fraction 0.85 --loogle-prefix-mix-mode chunked --loogle-prefix-chunk-size 180 --loogle-prefix-strict-cold --static-q-values 4000 --aimd-jain-threshold 0.72 --aimd-ttft-slo-ms 4000 --loogle-max-input-tokens 12000 --timeout 2400 --stop-service-at-end

Static-DLPM extension:
set AIMD_MULT_FACTOR=0.65 && python benchmark_modal_service_loogle_prefix_grid.py --policies dlpm --rates 5 --ks 1.0 --request-counts 1800 --max-concurrency 8 --loogle-prefix-dominant-fraction 0.85 --loogle-prefix-mix-mode chunked --loogle-prefix-chunk-size 180 --loogle-prefix-strict-cold --static-q-values 1200,8000 --aimd-jain-threshold 0.72 --aimd-ttft-slo-ms 4000 --loogle-max-input-tokens 12000 --timeout 2400 --stop-service-at-end

## Run Health

This merged view is healthy and complete:
- all six run files are present
- summary files were generated
- success rates are effectively 100% for all policies (fcfs has one failed request)

## Topline Results (Overall TTFT P99, lower is better)

1. adaptive_dlpm: 661.8 ms
2. dlpm_q1200: 682.8 ms
3. dlpm_q8000: 700.4 ms
4. dlpm_q4000: 713.3 ms
5. fcfs: 1098.4 ms
6. lpm: 1264.2 ms

Throughput is almost tied (about 46.08 to 46.15 tok/s), so ranking is driven by scheduling behavior, not throughput tradeoff.

## Dominant vs Cold Breakdown

Dominant TTFT P99:
1. adaptive_dlpm: 554.0 ms
2. dlpm_q1200: 604.9 ms
3. dlpm_q8000: 634.8 ms
4. dlpm_q4000: 639.9 ms
5. fcfs: 1080.4 ms
6. lpm: 1096.3 ms

Cold TTFT P99:
1. dlpm_q1200: 916.0 ms
2. dlpm_q8000: 961.4 ms
3. adaptive_dlpm: 1010.3 ms
4. dlpm_q4000: 1103.0 ms
5. fcfs: 1144.0 ms
6. lpm: 1805.5 ms

Key signal:
- lpm is clearly worst for cold-tail latency.
- fcfs is not best; it is second-worst on cold tails here.

## Interpretation Against Your Goal

If your desired story is "fcfs and adaptive best, lpm worst":
- lpm worst: yes
- adaptive best: yes overall and dominant, but not best in cold-only (dlpm_q1200/q8000 are better)
- fcfs best: no

So this strongly supports an anti-starvation claim for adaptive vs lpm, but does not support an fcfs-best claim in this high-dominant/high-locality regime.

## Recommended Next Step

If you still want fcfs to improve while keeping starvation pressure visible, use a less extreme dominant skew:

set AIMD_MULT_FACTOR=0.65 && python benchmark_modal_service_loogle_prefix_grid.py --policies adaptive_dlpm,fcfs,lpm,dlpm --rates 5 --ks 1.0 --request-counts 1800 --max-concurrency 8 --loogle-prefix-dominant-fraction 0.7 --loogle-prefix-mix-mode chunked --loogle-prefix-chunk-size 120 --loogle-prefix-strict-cold --static-q-values 1200,4000,8000 --aimd-jain-threshold 0.72 --aimd-ttft-slo-ms 4000 --loogle-max-input-tokens 12000 --timeout 2400 --stop-service-at-end

Why:
- lowering dominant-fraction from 0.85 to 0.7 reduces locality over-bias,
- fcfs usually improves relative to locality-focused policies,
- but lpm cold-tail weakness can still remain visible.

## Files Generated

- loogle_starvation_v4_summary.md
- loogle_starvation_v4_throughput_vs_rate.png
- loogle_starvation_v4_ttft_p99_vs_rate.png
- loogle_starvation_v4_pareto.png
- loogle_starvation_v4_ttft_percentile_hist.png
- loogle_starvation_v4_ttft_request_hist.png
- loogle_starvation_v4_request_total_hist.png
- loogle_starvation_v4_subset_breakdown.png
- loogle_starvation_v4_aimd_overview.png
- loogle_starvation_v4_aimd_traces/
- analysis_summary.md
