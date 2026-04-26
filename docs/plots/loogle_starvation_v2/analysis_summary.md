# LooGLE Fairness-Focused Analysis (V2)

Date: 2026-04-25
Input run: results/modal_grid_20260425_163753
Plot folder: docs/plots/loogle_starvation_v2

## Setup

Command used:
python benchmark_modal_service_grid.py --dataset loogle --policies adaptive_dlpm,fcfs,lpm,dlpm --rates 1.0 --ks 1.0 --request-counts 25,50 --max-concurrency 2 --static-q-values 1200,4000,8000 --aimd-jain-threshold 0.63 --stop-service-at-end

Policies covered:
- adaptive_dlpm
- fcfs
- lpm
- dlpm_q1200, dlpm_q4000, dlpm_q8000

## High-Level Verdict

This is only a partial match to your fairness-first target.

Your target was:
1. FCFS and adaptive_dlpm do best
2. LPM does worst

What happened:
1. FCFS is best on tail latency (good)
2. LPM is second-best, not worst (not what you wanted)
3. adaptive_dlpm is worse than LPM and FCFS in this slice, especially at n=25

So this run supports a fairness-favoring FCFS story, but not a strong adaptive-wins and LPM-worst story.

## Key Results

### n=50 (more stable than n=25)
By TTFT P99 (best to worst):
- fcfs: 998.35 ms
- lpm: 1039.97 ms
- adaptive_dlpm: 1084.85 ms
- dlpm_q4000: 1230.95 ms
- dlpm_q1200: 1308.26 ms
- dlpm_q8000: 1383.57 ms

At n=50, FCFS is best as desired. But LPM beats adaptive_dlpm, so fairness-first ordering is incomplete.

### n=25 (heavy tail outliers)
By TTFT P99 (best to worst):
- fcfs: 18013.31 ms
- lpm: 19444.65 ms
- dlpm_q4000: 25385.65 ms
- adaptive_dlpm: 27753.32 ms
- dlpm_q1200: 27924.94 ms
- dlpm_q8000: 30341.71 ms

At n=25, all policies show severe tails; FCFS still leads, but adaptive_dlpm is near the bottom.

### Throughput
Throughput is basically tied across policies:
- around 8.17 tok/s at n=25
- around 9.22 tok/s at n=50

This means your comparisons are primarily latency/fairness effects, not throughput tradeoffs.

## Adaptive Controller Readout

- rows_with_aimd_violated=true: 211 (out of 3414)
- adaptive median Q_at_scheduling: 2700

Interpretation:
- Adaptive is active (not fully clamped), but it still did not beat FCFS/LPM here.
- This likely means the workload does not create enough explicit hot-vs-cold unfairness pressure for adaptive control to dominate.

## Why LPM Is Not Worst Here

Two main reasons:
1. Dataset mode is plain loogle with no explicit dominant/cold split fields in summary (dominant/cold sections are empty in plots).
2. max_concurrency=2 keeps the queue shallow, reducing scheduling contention and reducing visible starvation effects.

So LPM does not get enough opportunity to exhibit strong unfairness pathologies here.

## Is This The Ideal Behavior You Wanted?

Not yet.

- Good: FCFS is best on P99, which fits fairness-priority.
- Missing: adaptive_dlpm does not outperform LPM.
- Missing: LPM is not worst.

## Recommended Next Run To Better Match Your Goal

If your goal is clearly fairness-first ordering (FCFS/adaptive best, LPM worst), increase unfairness pressure and queue contention.

### Option A: stay on benchmark_modal_service_grid.py (minimal change)
python benchmark_modal_service_grid.py --dataset loogle --policies adaptive_dlpm,fcfs,lpm,dlpm --rates 2.0,3.0 --ks 1.0 --request-counts 50,100 --max-concurrency 8 --static-q-values 1200,4000,8000 --aimd-jain-threshold 0.63 --stop-service-at-end

Why:
- higher rates + larger counts + higher concurrency increase queue pressure
- stronger pressure usually reveals fairness differences more clearly

### Option B: preferred for explicit starvation/fairness contrast
Use loogle_prefix benchmark (dominant vs cold split) with chunked mixing, e.g.
set AIMD_MULT_FACTOR=0.65 && python benchmark_modal_service_loogle_prefix_grid.py --request-counts 1500 --loogle-prefix-dominant-fraction 0.5 --loogle-prefix-mix-mode chunked --loogle-prefix-chunk-size 40 --max-concurrency 8 --aimd-jain-threshold 0.63 --rates 4 --static-q-values 1200,4000,8000 --aimd-ttft-slo-ms 4000 --stop-service-at-end --loogle-prefix-strict-cold

Why:
- explicit hot/cold competition makes LPM starvation behavior much easier to expose
- adaptive has a clearer chance to improve fairness tails

## Files Produced

- loogle_starvation_v2_summary.md
- loogle_starvation_v2_throughput_vs_rate.png
- loogle_starvation_v2_ttft_p99_vs_rate.png
- loogle_starvation_v2_pareto.png
- loogle_starvation_v2_ttft_percentile_hist.png
- loogle_starvation_v2_ttft_request_hist.png
- loogle_starvation_v2_request_total_hist.png
- loogle_starvation_v2_subset_breakdown.png
- loogle_starvation_v2_aimd_overview.png
- loogle_starvation_v2_aimd_violation_reasons.png
- loogle_starvation_v2_aimd_traces/
- analysis_summary.md (this file)
