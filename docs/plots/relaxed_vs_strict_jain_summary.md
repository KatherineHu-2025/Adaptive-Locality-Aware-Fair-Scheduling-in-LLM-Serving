# Relaxed vs Strict Jain Threshold Summary

Date: 2026-04-14

## Goal
Evaluate Adaptive DLPM behavior under two AIMD fairness thresholds:
- Strict: `AIMD_JAIN_THRESHOLD=0.95`
- Relaxed: `AIMD_JAIN_THRESHOLD=0.50`

The run used `run_aimd_ab_test_v2.py` with warmup and two-phase probes (Phase A then Phase B).

## Overall Results (200 requests per case)

| Case | Throughput (tok/s) | TTFT P50 (ms) | TTFT P95 (ms) | TTFT P99 (ms) |
|---|---:|---:|---:|---:|
| Strict | 179.377 | 934.132 | 1886.541 | 1983.051 |
| Relaxed | 179.356 | 2341.278 | 2842.521 | 3105.028 |

## Phase-Level Highlights

## Phase Workload Design (Phase 1 vs Phase 2)

Why there are two phases in the same run:
- A single-phase run can show whether AIMD is active, but it is less informative about adaptation to workload shifts.
- Two phases force a controlled traffic change in one continuous run so we can observe whether Q responds in the expected direction.

Phase 1 (Phase A) workload:
- Purpose: establish a lower-stress baseline under more regular arrivals.
- Parameters: `rate=1.0`, `k=1.0`, `dominant=60`, `cold=40`.
- Interpretation target: controller behavior when load is moderate and comparatively stable.

Phase 2 (Phase B) workload:
- Purpose: apply higher stress and burstiness to challenge fairness/latency control.
- Parameters: `rate=3.0`, `k=0.5`, `dominant=60`, `cold=40`.
- Interpretation target: whether AIMD tightens/loosens Q appropriately under harder conditions.

Why this helps analysis:
- Keeps client mix constant while changing only arrival dynamics and offered load.
- Makes strict vs relaxed comparison fair because both cases see the same phase transition.
- Improves visibility into directionality (up/down) and potential reversals in Q.

### Strict (0.95)
- Phase A (`rate=1.0, k=1.0`):
  - Throughput 89.699 tok/s, TTFT P50 308.790 ms, TTFT P99 1158.468 ms
- Phase B (`rate=3.0, k=0.5`):
  - Throughput 187.538 tok/s, TTFT P50 1662.056 ms, TTFT P99 1986.973 ms

### Relaxed (0.50)
- Phase A (`rate=1.0, k=1.0`):
  - Throughput 89.688 tok/s, TTFT P50 1037.563 ms, TTFT P99 2678.691 ms
- Phase B (`rate=3.0, k=0.5`):
  - Throughput 128.803 tok/s, TTFT P50 2627.282 ms, TTFT P99 3116.712 ms

## AIMD Dynamics Observed

### Strict (0.95)
- Sawtooth summary:
  - `q_min=1200.0`, `q_max=2800.0`
  - `has_up=false`, `has_down=true`, `direction_changes=0`, `sawtooth_like=false`
- Interpretation: Q moved down and then stayed near lower bound.

### Relaxed (0.50)
- Sawtooth summary:
  - `q_min=4250.0`, `q_max=14000.0`
  - `has_up=true`, `has_down=false`, `direction_changes=0`, `sawtooth_like=false`
- Interpretation: Q moved up monotonically and did not reverse.

## Interpretation
1. AIMD is active in both cases (Q updates occurred), but neither case produced oscillatory/sawtooth behavior.
2. Strict materially outperformed relaxed on tail latency while keeping similar overall throughput.
3. Relaxed drove Q much higher, which correlated with substantially worse TTFT and weaker high-load Phase B throughput.
4. This suggests current thresholds are on opposite extremes for this workload:
   - 0.95 pushes toward continuous tightening.
   - 0.50 pushes toward continuous loosening.

## Recommended Next Benchmarking Steps

### 1) Establish policy baselines first (FCFS and LPM)
Run a controlled grid before tuning AIMD so you know the fairness/latency envelope:

```powershell
python benchmark_modal_service_grid.py \
  --policies fcfs,lpm \
  --rates 0.5,1.0,1.5,2.0,3.0 \
  --ks 0.5,1.0,2.0 \
  --request-counts 50,100 \
  --arrival-mode per-client \
  --max-concurrency 4 \
  --timeout 600
```

Use these baseline outputs to define:
- Acceptable TTFT P99 ceiling
- Minimum throughput target
- Fairness floor (Jain) that still keeps latency practical

### 2) Add static DLPM reference points
Benchmark `dlpm` with several fixed Q values to find the best static frontier.
(Use the same workload grid used in Step 1 for comparability.)

### 3) Tune AIMD around observed regime boundary
Given observed AIMD-side Jain around ~0.53, sweep thresholds near that band instead of extremes:
- Candidate thresholds: `0.52, 0.54, 0.56, 0.58`
- Keep workload fixed while sweeping one AIMD parameter at a time.

Suggested first sweep:
- `AIMD_JAIN_THRESHOLD` near 0.53 to 0.58
- Then `AIMD_ADDITIVE_STEP` (smaller step can reduce one-way drift)
- Then `AIMD_MULT_FACTOR` (stronger pull can help reversals)

### 4) Use a three-phase load profile to induce reversals
To test true adaptivity, run low -> high -> low traffic in one case and verify:
- Q rises in low-load region
- Q falls in high-load region
- Q rises again after load relaxes

### 5) Decision criterion for final adaptive config
Choose AIMD settings that meet all three:
1. Near-LPM throughput under moderate load
2. Better tail latency than relaxed/high-Q settings
3. More stable fairness than pure LPM under bursty `k < 1` runs

## Artifacts from this run
- `results/probe_strict_jain_v2.jsonl`
- `results/probe_relaxed_jain_v2.jsonl`
- `results/probe_strict_jain_v2_aimd_run.json`
- `results/probe_relaxed_jain_v2_aimd_run.json`
- `docs/plots/plot_strict_v2.png`
- `docs/plots/plot_relaxed_v2.png`
- `docs/plots/plot_ab_compare_v2.png`
