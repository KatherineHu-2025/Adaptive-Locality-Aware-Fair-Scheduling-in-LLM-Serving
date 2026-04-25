# Analysis: modal_grid_20260423_204639

## Run Context
- Results folder: `results/modal_grid_20260423_204639`
- Exact benchmark command:

```powershell
python benchmark_modal_service_loogle_prefix_grid.py --request-counts 600 --loogle-prefix-dominant-fraction 0.5 --loogle-prefix-mix-mode chunked --loogle-prefix-chunk-size 40 --max-concurrency 8 --aimd-jain-threshold 0.72 --rates 4 --static-q-values 4000 --aimd-ttft-slo-ms 3800 --stop-service-at-end --loogle-prefix-strict-cold .
```

## Short Read
This run is balanced 300 dominant / 300 cold requests at rate 4.0 with a single static DLPM point at Q=4000, plus adaptive DLPM initialized around the same range. Throughput is very similar across policies, but tail latency remains large for all of them. The updated front-focused AIMD request-index plot makes the early-window behavior much easier to read, while the log-scaled x-axis compresses the long tail.

## Key Findings
- `dlpm` has the highest throughput in the summary, but it also has the worst overall TTFT P99 and the worst cold TTFT P99.
- `adaptive_dlpm` is slightly below static `dlpm` on throughput, but it is noticeably better on TTFT tail than `dlpm` and better than `lpm` on overall TTFT P99.
- `fcfs` has the best overall TTFT P99 and best dominant TTFT P99 in this run, which means locality-first scheduling is not dominating the tail here.
- `lpm` is competitive on median TTFT, but its P99 is still high and worse than `fcfs` and `adaptive_dlpm`.
- The cold subset is still expensive across all policies, with P99 TTFT in the 4.3s to 5.4s range.
- The dominant subset is the real stress point: dominant TTFT P99 stays above 21s for every policy, so the system is spending a lot of time serving the repeated long-context stream.

## Interpretation
The run does not show a clear win for adaptive DLPM under this configuration. The workload is still dominated by long requests and the fairness/locality tradeoff remains tight. Static DLPM gives the best throughput, but it pays for that with the worst tail latency. Adaptive DLPM lands in the middle: better tail behavior than static DLPM, but not enough to beat FCFS on P99 here.

The strict-cold mode is probably doing what it is supposed to do, but it does not eliminate high cached lengths entirely because the workload still contains large prompts and prefix reuse within the dominant stream. The log-scaled AIMD plots should make it easier to inspect how Q evolves early in the run without losing the long tail.

## Useful Artifact Locations
- Throughput plot: `docs/plots/loogle_prefix_v2/modal_grid_20260423_204639_throughput_vs_rate.png`
- TTFT P99 plot: `docs/plots/loogle_prefix_v2/modal_grid_20260423_204639_ttft_p99_vs_rate.png`
- Request TTFT history: `docs/plots/loogle_prefix_v2/modal_grid_20260423_204639_ttft_request_hist.png`
- End-to-end request history: `docs/plots/loogle_prefix_v2/modal_grid_20260423_204639_request_total_hist.png`
- AIMD overview: `docs/plots/loogle_prefix_v2/modal_grid_20260423_204639_aimd_overview.png`
- Per-run AIMD trace(s): `docs/plots/loogle_prefix_v2/modal_grid_20260423_204639_aimd_traces/`
