# LooGLE Starvation V3 Analysis

Date: 2026-04-25
Input: results/modal_grid_20260425_220710
Plots: docs/plots/loogle_starvation_v3

## Command Used

set AIMD_MULT_FACTOR=0.65 && python benchmark_modal_service_loogle_prefix_grid.py --policies adaptive_dlpm,fcfs,lpm,dlpm --rates 4 --ks 1.0 --request-counts 1200 --max-concurrency 8 --loogle-prefix-dominant-fraction 0.3 --loogle-prefix-mix-mode chunked --loogle-prefix-chunk-size 60 --loogle-prefix-strict-cold --static-q-values 1200,4000,8000 --aimd-jain-threshold 0.68 --aimd-ttft-slo-ms 4000 --loogle-max-input-tokens 26000 --timeout 3000 --stop-service-at-end

## Quick Verdict

This run does **not** match the fairness-first behavior you wanted (adaptive/fcfs best, lpm worst).

Observed ordering by overall TTFT P99:
1. lpm: 5517 ms (best)
2. dlpm_q8000: 5538 ms
3. adaptive_dlpm: 5636 ms
4. dlpm_q1200: 5657 ms
5. dlpm_q4000: 5774 ms
6. fcfs: 6089 ms (worst)

So the opposite happened: lpm best, fcfs worst.

## Subgroup (Dominant vs Cold) Findings

This run has meaningful subgroup data because loogle_prefix generated dominant/cold clients.

### Dominant clients (TTFT P99)
1. lpm: 3296 ms (best)
2. dlpm_q1200: 4359 ms
3. dlpm_q8000: 4806 ms
4. adaptive_dlpm: 4904 ms
5. dlpm_q4000: 5127 ms
6. fcfs: 5614 ms (worst)

### Cold clients (TTFT P99)
1. dlpm_q8000: 5631 ms (best)
2. dlpm_q1200: 5746 ms
3. dlpm_q4000: 5934 ms
4. adaptive_dlpm: 5982 ms
5. lpm: 6008 ms
6. fcfs: 6089 ms (worst)

Interpretation:
- lpm is still very strong on dominant clients (expected under locality).
- lpm is not worst on cold tails either (fcfs is worse here).
- adaptive is in the middle, not winning cold tails.

## Why This Likely Happened

1. dominant fraction is 0.3 (cold-majority), which weakens the classic locality-starvation effect where lpm heavily favors a large hot cohort.
2. adaptive controller is effectively clamped low (median Q_at_scheduling=1200), so adaptive behaves close to fairness-biased dlpm but does not beat static variants in this run.
3. fcfs had non-trivial failures (success_rate 98.58%), which hurt its tail metrics and made it look worst.

## Stability Check

This run is much healthier than the previous failed attempt:
- all six run files are present
- summary.csv and summary.json were produced
- adaptive had rich AIMD telemetry (rows_with_aimd_violated=true: 1186)

## What To Do Next

If your target is specifically: adaptive/fcfs best and lpm worst, run a more fairness-stress setting that increases queue pressure and hot-client dominance.

Recommended next command:

set AIMD_MULT_FACTOR=0.65 && python benchmark_modal_service_loogle_prefix_grid.py --policies adaptive_dlpm,fcfs,lpm,dlpm --rates 4,6 --ks 1.0 --request-counts 1200,1800 --max-concurrency 12 --loogle-prefix-dominant-fraction 0.7 --loogle-prefix-mix-mode chunked --loogle-prefix-chunk-size 120 --loogle-prefix-strict-cold --static-q-values 1200,4000,8000 --aimd-jain-threshold 0.72 --aimd-ttft-slo-ms 4000 --loogle-max-input-tokens 12000 --timeout 1800 --stop-service-at-end

Why these changes:
1. dominant-fraction 0.7 + chunk-size 120: stronger hot-vs-cold competition, easier to expose lpm unfairness.
2. concurrency 12 + rates 4,6: deeper queue and stronger contention.
3. jain-threshold 0.72: pushes adaptive to react earlier to unfairness.
4. max-input-tokens 12000: reduces service instability from very long-prefill extremes while keeping fairness pressure.

## Files Generated in v3

- loogle_starvation_v3_summary.md
- loogle_starvation_v3_throughput_vs_rate.png
- loogle_starvation_v3_ttft_p99_vs_rate.png
- loogle_starvation_v3_pareto.png
- loogle_starvation_v3_ttft_percentile_hist.png
- loogle_starvation_v3_ttft_request_hist.png
- loogle_starvation_v3_request_total_hist.png
- loogle_starvation_v3_subset_breakdown.png
- loogle_starvation_v3_aimd_overview.png
- loogle_starvation_v3_aimd_violation_reasons.png
- loogle_starvation_v3_aimd_traces/
- analysis_summary.md
