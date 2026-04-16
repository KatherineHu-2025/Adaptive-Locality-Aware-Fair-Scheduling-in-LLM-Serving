# Relaxed 0.55 vs Strict Jain Threshold Summary

Date: 2026-04-16
Source artifacts: docs/plots/relaxed_55p

## Goal
Evaluate Adaptive DLPM behavior with:
- Strict case: AIMD_JAIN_THRESHOLD=0.95
- Relaxed case: AIMD_JAIN_THRESHOLD=0.55

The run used warmup plus two-phase probe flow (Phase A then Phase B), with 200 requests total per case.

## How to Reproduce
python run_aimd_ab_test_v2.py --server https://emilyho--adaptive-dlpm-scheduler-service-hosted-minisgl-app.modal.run --app-name adaptive-dlpm-scheduler-service --strict-jain-threshold 0.95 --relaxed-jain-threshold 0.55 --output-dir docs/plots/relaxed_55p_strict_95p

## Overall Results (200 requests per case)

| Case | Throughput (tok/s) | TTFT P50 (ms) | TTFT P95 (ms) | TTFT P99 (ms) |
|---|---:|---:|---:|---:|
| Strict (0.95) | 179.369 | 2570.823 | 2968.769 | 4573.006 |
| Relaxed (0.55) | 179.383 | 879.367 | 1793.183 | 2328.771 |

Key deltas (Relaxed 0.55 vs Strict 0.95):
- Throughput: essentially tied (difference about 0.014 tok/s, less than 0.01%).
- TTFT P50: improved by about 65.8%.
- TTFT P95: improved by about 39.6%.
- TTFT P99: improved by about 49.1%.

## Phase-Level Results

### Strict (0.95)
- Phase A (rate=1.0, k=1.0, dominant=60, cold=40):
  - Throughput 89.695 tok/s, TTFT P50 1356.073 ms, TTFT P99 5067.141 ms
- Phase B (rate=3.0, k=0.5, dominant=60, cold=40):
  - Throughput 123.994 tok/s, TTFT P50 2733.571 ms, TTFT P99 3074.907 ms

### Relaxed (0.55)
- Phase A (rate=1.0, k=1.0, dominant=60, cold=40):
  - Throughput 89.702 tok/s, TTFT P50 323.476 ms, TTFT P99 2517.215 ms
- Phase B (rate=3.0, k=0.5, dominant=60, cold=40):
  - Throughput 197.638 tok/s, TTFT P50 1495.351 ms, TTFT P99 2006.523 ms

Notable phase observations:
- Phase A throughput is nearly identical between cases, but 0.55 has much better latency.
- Phase B shows major gains for 0.55: throughput is about 59.4% higher than strict, with better tail latency.

## AIMD Dynamics

### Strict (0.95)
- Updates: 40
- Q range: 1200 to 2800
- Sawtooth summary:
  - has_up=false, has_down=true
  - direction_changes=0
  - sawtooth_like=false

Interpretation: controller mostly tightened and saturated near low Q, with no recovery oscillation.

### Relaxed (0.55)
- Updates: 40
- Q range: 1200 to 8500
- Sawtooth summary:
  - has_up=true, has_down=true
  - direction_changes=5
  - sawtooth_like=true

Interpretation: controller exhibited true adaptive behavior (both increase and decrease), matching the intended AIMD pattern.

## Practical Interpretation

1. 0.55 appears much better calibrated for this workload than 0.95.
2. 0.95 is too strict in this setup, driving one-way tightening and worse latency.
3. 0.55 keeps throughput at least as good and strongly improves TTFT percentiles.
4. This run is the strongest evidence so far that moving the Jain threshold near the observed operating band (around 0.55) is beneficial.

## Artifacts Used

- probe_strict_jain_v2.jsonl
- probe_relaxed_jain_v2.jsonl
- probe_strict_jain_v2_aimd_run.json
- probe_relaxed_jain_v2_aimd_run.json
- probe_strict_phase_a_v2.jsonl
- probe_strict_phase_b_v2.jsonl
- probe_relaxed_phase_a_v2.jsonl
- probe_relaxed_phase_b_v2.jsonl
- plot_strict_v2.png
- plot_relaxed_v2.png
- plot_ab_compare_v2.png
