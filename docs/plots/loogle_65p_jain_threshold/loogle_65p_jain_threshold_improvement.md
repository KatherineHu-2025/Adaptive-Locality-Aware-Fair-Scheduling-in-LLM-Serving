# LooGLE 0.65 Jain Threshold Improvement Summary

This summary compares:

- New adaptive run (relaxed Jain threshold): `results/modal_grid_20260421_150551/summary.csv`
- Previous baseline run set: `results/modal_grid_20260419_160306/summary.csv`

Scope is fixed to `dataset=loogle`, `rate=1.0`, `k=1.0`, with request counts `n in {25,50}`.

Generated plots in this folder include:

- Baseline policy comparison set (throughput, TTFT, pareto, AIMD traces)
- Old-vs-new adaptive plot: `loogle_65p_jain_threshold_old_vs_new_adaptive.png`

## New Plot Catalog (Old vs New Focus)

This section lists all newly generated plots that directly compare the new adaptive run against old references.

### 1) Old Adaptive vs New Adaptive (single figure, 4 panels)

- File path: `docs/plots/loogle_65p_jain_threshold/loogle_65p_jain_threshold_old_vs_new_adaptive.png`
- What it is: A side-by-side bar figure comparing old adaptive (`modal_grid_20260419_160306`) vs new adaptive (`modal_grid_20260421_150551`) at `rate=1.0`, `k=1.0`, for `n=25` and `n=50`.
- Panels and interpretation:
    - TTFT P50 panel: Lower is better. New adaptive is much lower at both `n=25` and `n=50`.
    - TTFT P99 panel: Lower is better. New adaptive substantially reduces tail latency, especially at `n=50`.
    - Throughput panel: Higher is better. Throughput is essentially unchanged at `n=50`, with a modest drop at `n=25`.
    - Success-rate panel: Higher is better. `n=50` is unchanged; `n=25` shows a small dip due to one failed request.
- Analysis takeaway: The relaxed Jain threshold mostly improves latency (both median and tail) while preserving throughput in the more stable `n=50` slice.

### 2) New Adaptive (0.65) vs Old Baseline Policies

- File path: `docs/plots/loogle_65p_jain_threshold/loogle_65p_jain_threshold_adaptive_vs_baselines_improvement.png`
- What it is: Improvement bars for adaptive(0.65) versus prior FCFS/DLPM/LPM baseline rows from `modal_grid_20260419_160306`, split by `n=25` and `n=50`.
- How to interpret:
    - Y-axis is TTFT P99 improvement (%).
    - Positive values mean adaptive(0.65) has lower P99 (better tail latency) than that baseline.
    - Negative values mean adaptive(0.65) is worse than that baseline.
- Analysis takeaway:
    - At `n=50`, adaptive(0.65) is positive versus all baselines.
    - At `n=25`, adaptive(0.65) is positive versus FCFS/LPM but slightly negative versus static DLPM.

### 3) Supporting Numeric Summary for Old-vs-New Interpretation

- File path: `docs/plots/loogle_65p_jain_threshold/loogle_65p_jain_threshold_improvement.md` (this file)
- What it is: Tabular percentage deltas that quantify what the two plots show.
- How to use with the plots:
    - Use the plots for quick visual ranking and pattern recognition.
    - Use the table values to report exact percentages in writeups/slides.
    - If there is visual ambiguity at `n=25`, trust repeated-run statistics over single-run bars.

## Adaptive (0.65) vs FCFS/DLPM/LPM

Positive TTFT improvement means lower latency than baseline. Positive throughput improvement means higher throughput than baseline.

```text
 request_count baseline  ttft_p99_improvement_pct  ttft_p50_improvement_pct  throughput_improvement_pct
            25     fcfs                     15.13                     52.75                       -2.45
            25     dlpm                     -3.15                     50.64                       -2.45
            25      lpm                     11.39                     17.11                       -2.45
            50     fcfs                     29.44                     47.54                        0.00
            50     dlpm                     33.31                     45.71                        0.00
            50      lpm                     13.69                     13.43                       -0.00
```

Interpretation:

- At `n=50`, adaptive(0.65) is clearly better than all three baselines on both P50 and P99 TTFT while keeping throughput essentially unchanged.
- At `n=25`, adaptive(0.65) still improves over FCFS and LPM, but static DLPM has a slightly better P99 in this low-sample slice.

Important clarification:

- The statement above is about **policy outcome comparison** (latency/throughput), not AIMD controller shape.
- In this run, `n=50` is not useful for seeing a sawtooth because AIMD is fully clamped by fairness violation.

## Old Adaptive vs New Adaptive (0.65)

The old adaptive run is from `modal_grid_20260419_160306` and the new adaptive run is from `modal_grid_20260421_150551`.

```text
 n    p50 improvement   p99 improvement   throughput delta   success rate delta
25        +55.79%          +22.03%           -2.4506%          -0.538 pp
50        +48.27%          +42.60%           +0.0004%          +0.000 pp
```

Interpretation:

- Relaxing Jain to 0.65 substantially reduced adaptive latency versus the old adaptive behavior, especially for tail latency at `n=50`.
- Throughput remained neutral at `n=50`, which suggests the latency gain did not come from sacrificing throughput in the more stable slice.
- The small `n=25` throughput/success drop likely reflects sensitivity to startup/outlier effects (one failed request in the new run).

## Clarification: Metric Stability vs AIMD Observability

These are two different questions:

1. **Metric stability for policy comparison**: how reliable TTFT/throughput comparisons are.
2. **AIMD observability**: whether Q actually moves enough to show controller behavior (for example, sawtooth-like patterns).

For the new adaptive run (`modal_grid_20260421_150551`):

- `n=50`: AIMD is violated on all rows (`383/383 = 100%`), violation reason is always `jain`, and `Q_at_scheduling` is fixed at `1200` (single value). This is **good for endpoint metric comparison**, but **not informative for AIMD dynamics**.
- `n=25`: AIMD violation rate is lower (`84/186 = 45.16%`), with mixed reasons (`none`: 102, `jain`: 84), and Q takes multiple values (`1200, 1500, 2000, 2500, 3000, 4000`; some rows have `-1` placeholder). This is **more informative for AIMD movement**, but **noisier for endpoint metrics** due to one failed request and stronger startup/outlier influence.

Bottom line:

- Your observation is correct: we should **not** describe `n=50` as "better" for AIMD pattern analysis in this run.
- `n=50` was only "more stable" in the narrower sense of policy endpoint metrics.

## What The More Relaxed Jain Threshold Appears To Do

Based on this comparison slice:

- It reduces over-tightening behavior in adaptive mode, allowing better latency outcomes (large P50 and P99 reductions vs old adaptive).
- It preserves practical fairness indicators in this setup (Jain values remain close to prior values in summary rows), while improving latency materially.
- It is most convincing at `n=50` for endpoint latency/throughput comparisons; however, `n=50` does not reveal AIMD dynamics because Q is clamped. `n=25` remains noisy but is more informative for controller movement.

This means `J=0.65` looks like a better operating point than the previous adaptive setup for this LooGLE condition, but should still be validated under higher pressure.

## Recommended Next Steps

1. Re-run `n=25` 3 to 5 times with different seeds and report median/iqr to de-noise startup effects.
2. Perform a narrow threshold sweep around this setting (`J in {0.60, 0.65, 0.70}`) at the same rate/k and compare old-vs-new style deltas.
3. Add higher-load checks (`rate=2.0` and `rate=3.0`) to confirm the improvement persists when queues are deeper.
4. Compare adaptive telemetry traces side-by-side (Q trajectory and violation reasons) between old and new runs to verify the mechanism behind the latency gains.
5. If `n=50` behavior replicates while `n=25` remains unstable, choose metrics based on repeated-run medians rather than single-run points.