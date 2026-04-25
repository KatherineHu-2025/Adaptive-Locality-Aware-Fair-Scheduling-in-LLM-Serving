# Analysis: modal_grid_20260424_001827

## Run Context
- Results folder: results/modal_grid_20260424_001827
- Exact command used:

```powershell
python benchmark_modal_service_loogle_prefix_grid.py --request-counts 2000 --loogle-prefix-dominant-fraction 0.5 --loogle-prefix-mix-mode chunked --loogle-prefix-chunk-size 40 --max-concurrency 8 --aimd-jain-threshold 0.72 --rates 4 --static-q-values 4000 --aimd-ttft-slo-ms 3800 --stop-service-at-end --loogle-prefix-strict-cold
```

## What Was Generated
- Full plot bundle under docs/plots/loogle_prefix_v3
- Summary table markdown from plot script
- This analysis markdown

## Headline Results
- Policies compared: adaptive_dlpm, dlpm_q4000, lpm, fcfs
- Rate/K/N: rate=4.0, k=1.0, request_count=2000
- Overall throughput leader: dlpm_q4000 (34.633 tok/s), effectively tied with adaptive_dlpm (34.630 tok/s)
- Overall TTFT P99 winner: fcfs (4347.046 ms)

## Detailed Observations
1. Throughput
- dlpm_q4000 and adaptive_dlpm are almost identical on throughput (~34.63 tok/s).
- lpm is lower (33.74 tok/s), fcfs is lowest (32.94 tok/s).

2. Overall Tail Latency (TTFT P99)
- fcfs is best overall (4347 ms).
- lpm is next (4472 ms).
- dlpm_q4000 is higher (4741 ms).
- adaptive_dlpm is highest among four (4801 ms).

3. Dominant vs Cold Split
- Dominant TTFT P99 best: dlpm_q4000 (1949 ms), then lpm (2325 ms), adaptive (2800 ms), fcfs (4099 ms).
- Cold TTFT P99 best: fcfs (4563 ms), then lpm (4814 ms), dlpm_q4000 (4986 ms), adaptive (5224 ms).
- This run shows a clear tradeoff: DLPM helps dominant clients most, while FCFS protects cold-client tail better.

4. Reliability / Coverage
- Total request rows: 8000 across all plotted runs.
- One static dlpm request failed (success_count=1999/2000); all others were 2000/2000.
- Adaptive AIMD telemetry present: 7999 rows with Q and Jain signals.
- AIMD violations flagged: 793 rows.

## Interpretation
- With this 50/50 dominant-cold mix and chunked arrivals, static dlpm_q4000 gives top throughput and strongest dominant-client tail.
- If your objective is overall or cold-client tail latency, fcfs remains strongest in this run.
- Adaptive DLPM did not beat static q=4000 on throughput or tail for this configuration; median adaptive Q was 3550, suggesting the controller spent substantial time below 4000.

## Useful Output Files
- docs/plots/loogle_prefix_v3/modal_grid_20260424_001827_throughput_vs_rate.png
- docs/plots/loogle_prefix_v3/modal_grid_20260424_001827_ttft_p99_vs_rate.png
- docs/plots/loogle_prefix_v3/modal_grid_20260424_001827_ttft_request_hist.png
- docs/plots/loogle_prefix_v3/modal_grid_20260424_001827_request_total_hist.png
- docs/plots/loogle_prefix_v3/modal_grid_20260424_001827_aimd_overview.png
- docs/plots/loogle_prefix_v3/modal_grid_20260424_001827_summary.md
