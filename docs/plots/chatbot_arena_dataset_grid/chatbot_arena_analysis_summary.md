# Chatbot Arena Benchmark Analysis

Run folder: results/modal_grid_20260414_234633  
Scope: 18 runs (3 policies x 3 rates x 2 k values), each with request_count=30 (31 observed requests/run)

## Executive Summary

- The benchmark completed successfully for all policy/rate/k combinations.
- Reliability was very high: 17/18 runs achieved 100% success; 1 run had a single failed request.
- Throughput was effectively tied across FCFS, LPM, and Adaptive-DLPM at the same offered load.
- At operational loads (rate=2.0 and 3.0), FCFS had the best TTFT p99 with no throughput penalty.
- At low load (rate=1.0), several runs across multiple policies showed severe tail-latency outliers, so conclusions at rate=1.0 should be treated cautiously.

## Dataset and Grid

- Dataset: chatbot_arena
- Policies: fcfs, lpm, adaptive_dlpm
- Rates: 1.0, 2.0, 3.0
- k values: 0.5, 1.0
- Request count target: 30

## Reliability

- 17/18 runs: success_rate = 1.0
- 1/18 run: success_rate = 0.9677 (Adaptive-DLPM, rate=1.0, k=1.0)
- The partial failure was an HTTP 408 timeout/cancellation in:
  - results/modal_grid_20260414_234633/runs/adaptive_dlpm_r1.0_k1.0_n30.jsonl

## Throughput Findings

- Median throughput by policy (rounded):
  - FCFS: 44.1 tok/s
  - LPM: 44.1 tok/s
  - Adaptive-DLPM: 44.1 tok/s
- Interpretation: scheduler choice did not materially change aggregate throughput in this setup.

## Tail-Latency Findings (TTFT p99)

### Best p99 per offered load

- rate=1.0: LPM (k=1.0), p99 ~ 4010 ms
- rate=2.0: FCFS (k=0.5), p99 ~ 2738 ms
- rate=3.0: FCFS (k=0.5), p99 ~ 2842 ms

### High-load behavior (rate=2.0 and 3.0)

- FCFS consistently delivered the best TTFT p99 while keeping throughput comparable to other policies.
- LPM and Adaptive-DLPM were generally around ~4.0-5.2s p99 in these regimes.

### Low-load anomaly (rate=1.0)

Several runs exhibited extreme p99 spikes:

- FCFS k=0.5: ~146724 ms
- FCFS k=1.0: ~159461 ms
- LPM k=0.5: ~23361 ms
- Adaptive-DLPM k=0.5: ~147506 ms

These spikes appear in multiple policies and likely reflect run-specific straggler/queueing behavior rather than a clean policy separation at rate=1.0.

## Fairness

- Jain index was nearly constant (~0.553) across almost all runs.
- Interpretation: this particular workload/configuration did not expose strong fairness differentiation between policies.

## Recommendation

- For this Chatbot Arena grid, FCFS is the safest latency choice at practical loads (rate 2-3), with no meaningful throughput downside.
- Re-run rate=1.0 with multiple seeds/trials before using those points for policy conclusions.

## Plotting Command

From repository root:

```powershell
.\venv\Scripts\python.exe plot_benchmark_result.py results/modal_grid_20260414_234633 --output-dir results/modal_grid_20260414_234633/plots --prefix chatbot_arena_grid
```

Expected outputs:

- results/modal_grid_20260414_234633/plots/chatbot_arena_grid_throughput_vs_rate.png
- results/modal_grid_20260414_234633/plots/chatbot_arena_grid_ttft_p99_vs_rate.png
- results/modal_grid_20260414_234633/plots/chatbot_arena_grid_pareto.png
- results/modal_grid_20260414_234633/plots/chatbot_arena_grid_summary.md
