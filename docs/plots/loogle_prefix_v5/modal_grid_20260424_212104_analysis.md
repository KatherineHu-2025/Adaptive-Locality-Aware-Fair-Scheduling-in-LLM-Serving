# Analysis: modal_grid_20260424_212104

## Run Context
- Results folder: results/modal_grid_20260424_212104
- Exact command used:

set AIMD_MULT_FACTOR=0.65 && python benchmark_modal_service_loogle_prefix_grid.py --request-counts 1500 --loogle-prefix-dominant-fraction 0.5 --loogle-prefix-mix-mode chunked --loogle-prefix-chunk-size 40 --max-concurrency 8 --aimd-jain-threshold 0.72 --rates 4 --static-q-values 4000 --aimd-ttft-slo-ms 4000 --stop-service-at-end --loogle-prefix-strict-cold

## v5 Standalone Summary
- Policies: adaptive_dlpm, dlpm_q4000, lpm, fcfs
- Request count per policy: 1500, all successful
- Throughput leader: adaptive_dlpm (34.433 tok/s)
- Best overall TTFT P99: lpm (4587.457 ms)
- Best dominant TTFT P99: adaptive_dlpm (2071.080 ms)
- Worst cold TTFT P99: adaptive_dlpm (5437.096 ms)

## Direct Comparison Against v3 and v4
Reference folders:
- v3: results/modal_grid_20260424_001827
- v4: results/modal_grid_20260424_184711

### Adaptive DLPM trajectory
- Throughput (tok/s):
  - v3: 34.630
  - v4: 32.935
  - v5: 34.433
  - v5 vs v4: +4.55%
  - v5 vs v3: -0.57%

- TTFT P99 (ms):
  - v3: 4801.150
  - v4: 6527.214
  - v5: 4907.639
  - v5 vs v4: improved strongly (-24.8%)
  - v5 vs v3: slightly worse (+2.2%)

- TTFT P50 (ms):
  - v3: 1342.664
  - v4: 1375.405
  - v5: 1043.319
  - v5 is best by a large margin

- Dominant TTFT P99 (ms):
  - v3: 2800.138
  - v4: 6900.288
  - v5: 2071.080
  - v5 is best

- Cold TTFT P99 (ms):
  - v3: 5224.436
  - v4: 6110.291
  - v5: 5437.096
  - v5 recovers from v4 but is still worse than v3

- Reliability:
  - v3 adaptive failures: 0
  - v4 adaptive failures: 29
  - v5 adaptive failures: 0

- Controller behavior:
  - Adaptive median Q:
    - v3: 3550
    - v4: 16000
    - v5: 1700
  - AIMD violation rows:
    - v3: 793 / 7999 (~9.9%)
    - v4: 211 / 15970 (~1.3%)
    - v5: 763 / 6000 (~12.7%)

## Interpretation
- v5 is clearly better than v4 for adaptive DLPM. It restored reliability and recovered both throughput and tail latency.
- Compared with v3, v5 is mixed:
  - better median and dominant behavior,
  - slightly worse adaptive TTFT P99,
  - worse cold-tail P99.
- Relative to other policies in v5:
  - adaptive wins throughput and dominant tail,
  - adaptive loses on cold-tail P99 and is not best overall P99.

## Is this ideal behavior?
Short answer: close, but not fully ideal yet.

What looks ideal:
- adaptive regained high throughput,
- adaptive dominant TTFT P99 is now best,
- adaptive failures dropped back to zero.

What is not ideal yet:
- adaptive cold-tail P99 remains worst,
- overall TTFT P99 is not best (lpm is better),
- high violation rate suggests control may still be too aggressive/noisy.

If your target is throughput + dominant performance without reliability regressions, v5 is a good direction. If your target includes cold-tail fairness and best overall P99, further tuning is still needed.

## Generated Artifacts
- docs/plots/loogle_prefix_v5/modal_grid_20260424_212104_throughput_vs_rate.png
- docs/plots/loogle_prefix_v5/modal_grid_20260424_212104_ttft_p99_vs_rate.png
- docs/plots/loogle_prefix_v5/modal_grid_20260424_212104_ttft_request_hist.png
- docs/plots/loogle_prefix_v5/modal_grid_20260424_212104_request_total_hist.png
- docs/plots/loogle_prefix_v5/modal_grid_20260424_212104_aimd_overview.png
- docs/plots/loogle_prefix_v5/modal_grid_20260424_212104_summary.md
