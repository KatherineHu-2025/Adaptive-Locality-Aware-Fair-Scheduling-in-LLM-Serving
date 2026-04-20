# LooGLE Updated Benchmark and Plot Analysis

Date: 2026-04-19  
Source results: results/modal_grid_20260419_160306  
Plot folder: docs/plots/loogle_updated_benchmark_and_plot

## Scope

This analysis covers the 8 benchmark rows in the current run set:

- Dataset: `loogle`
- Policies: `adaptive_dlpm`, `dlpm`, `fcfs`, `lpm`
- Arrival settings: `rate=1.0`, `k=1.0`
- Request counts: `n=25`, `n=50`

## Headline Findings

1. Throughput is effectively tied across all four policies.
2. At this workload slice, `lpm` has the best latency (both TTFT P50 and TTFT P99), while throughput remains almost identical to the others.
3. TTFT tails are much worse at `n=25` than `n=50` for all policies (large one-time startup/tail effect).
4. Adaptive AIMD behavior is dominated by fairness violations (`jain`), which quickly drives and keeps `Q` at `Q_min=1200`.

## Core Metrics (from summary.csv)

### n=50 (most stable comparison point)

| Policy | Throughput (tok/s) | TTFT P50 (ms) | TTFT P99 (ms) |
|---|---:|---:|---:|
| lpm | 9.2170 | 737.69 | 1925.47 |
| fcfs | 9.2169 | 1217.46 | 2355.06 |
| dlpm | 9.2169 | 1176.43 | 2491.66 |
| adaptive_dlpm | 9.2169 | 1234.66 | 2895.08 |

Interpretation:

- Throughput spread is tiny (roughly 9.2169 to 9.2170 tok/s), so latency differences matter more than throughput in this slice.
- `lpm` is the latency winner here.

### n=25 to n=50 shift

- Throughput increases by ~12.84% to ~12.85% for every policy.
- TTFT P99 improves sharply for every policy:
  - adaptive_dlpm: ~90.81% drop
  - dlpm: ~89.53% drop
  - fcfs: ~91.86% drop
  - lpm: ~93.05% drop

Interpretation:

- The n=25 runs include a strong early tail effect (large TTFT outliers).
- n=50 is the more representative view for policy comparison in this folder.

## Adaptive AIMD Behavior

Using adaptive request logs:

- `adaptive_dlpm_r1.0_k1.0_n25.jsonl`
  - rows: 186
  - Q range: min 1200, median 1200, max 4000, unique Q values: 3
  - violation rate: 90.86%
  - top reasons: `jain` 169, `none` 17

- `adaptive_dlpm_r1.0_k1.0_n50.jsonl`
  - rows: 383
  - Q range: min 1200, median 1200, max 1200, unique Q values: 1
  - violation rate: 100%
  - top reasons: `jain` 383

Combined adaptive view:

- rows: 569
- violation rate: 97.01%
- reasons: `jain` 552, `none` 17

Interpretation:

- AIMD is almost always in violation mode due to Jain threshold condition.
- Controller spends nearly all time at low quota (`Q=1200`), so the adaptive policy behaves close to a strict fairness regime in this workload.

## Plot Reading Guide

Main artifacts in this folder:

- Throughput vs rate: `loogle_updated_benchmark_and_plot_throughput_vs_rate.png`
- TTFT P99 vs rate: `loogle_updated_benchmark_and_plot_ttft_p99_vs_rate.png`
- TTFT histograms: `loogle_updated_benchmark_and_plot_ttft_percentile_hist.png`, `loogle_updated_benchmark_and_plot_ttft_request_hist.png`
- AIMD overview: `loogle_updated_benchmark_and_plot_aimd_overview.png`
- Per-run AIMD traces (all adaptive runs):
  - `loogle_updated_benchmark_and_plot_aimd_traces/trace_001_r1_k1_n25.png`
  - `loogle_updated_benchmark_and_plot_aimd_traces/trace_002_r1_k1_n50.png`

## Practical Conclusions for This Folder

1. For this exact LooGLE slice (`rate=1.0`, `k=1.0`, `n in {25,50}`), `lpm` gives the best latency while throughput remains tied.
2. Adaptive DLPM currently appears over-constrained by fairness thresholding (`jain` violations dominate), leading to persistent low Q.
3. This folder is useful as a controlled low-load baseline and AIMD-behavior diagnostic, but not yet a strong win case for adaptive DLPM.

## Suggested Next Pass

1. Repeat this exact setup at higher rates (`2.0`, `3.0`) to test whether adaptive behavior becomes beneficial under queue pressure.
2. Run a small threshold sweep (for example `AIMD_JAIN_THRESHOLD=0.55/0.65/0.75`) and compare Q trajectory + TTFT tails.
3. Keep the new per-run AIMD traces; they are the clearest way to confirm whether Q is adapting vs clamped.
