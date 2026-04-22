# Adaptive DLPM (J=0.63) Policy Analysis

Date: 2026-04-21

## Scope

This note analyzes adaptive DLPM at Jain threshold 0.63 against FCFS, DLPM, and LPM using:

- results/modal_grid_20260421_185446/summary.csv
- dataset: loogle
- rate: 1.0
- k: 1.0
- request_count: 25, 50, 100

Interpretation for deltas:

- P50/P99 improvement (%): positive means adaptive has lower latency (better)
- Throughput delta (%): positive means adaptive has higher throughput (better)
- Success-rate delta (pp): positive means adaptive has higher success rate (better)

## Adaptive Raw Metrics

```text
 request_count  success_rate  throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
            25      1.000000                8.167641     573.0447   18220.3575
            50      1.000000                9.216925     698.1283    3274.9426
           100      0.998744                8.519966    1364.6796    6602.7925
```

## Adaptive vs Other Policies

```text
   n baseline  p50_impr_pct  p99_impr_pct  thr_delta_pct  sr_delta_pp
  25     fcfs        -28.99         13.70          -0.00         0.00
  25     dlpm         -3.96         37.03           0.00         0.00
  25      lpm         96.13         39.88           0.00         0.00
  50     fcfs        -24.89        -27.01          -0.00         0.00
  50     dlpm         -3.59         -5.35          -0.00         0.00
  50      lpm         95.17         97.74           1.31         0.00
 100     fcfs        -25.74        -58.53          -0.05        -0.13
 100     dlpm         -9.29         10.61          -0.05        -0.13
 100      lpm         -0.66         -9.46          -0.05        -0.13
```

## What This Means

1. At n=25, adaptive improves tail latency strongly versus DLPM and LPM, and still improves P99 versus FCFS, but it has worse median latency than FCFS and DLPM.
2. At n=50, adaptive is clearly better than LPM, but loses to FCFS and DLPM on both P50 and P99.
3. At n=100, adaptive beats static DLPM on P99 (+10.61%), but trails FCFS and LPM on both median and tail latency, with a small success-rate drop (one failed request).
4. Throughput is effectively tied across FCFS, adaptive, and DLPM (differences near 0%), except that adaptive outperforms LPM at n=50 due to LPM degradation.

## Conclusion

For this 0.63 configuration and workload slice, adaptive DLPM is not the global latency winner across all policies. It is best described as a robust middle-ground policy:

1. It consistently avoids catastrophic LPM behavior.
2. It can outperform static DLPM on tail latency at higher load (n=100), but not always at medium load (n=50).
3. FCFS remains the strongest pure-latency baseline in this particular run set, especially at n=50 and n=100.

Practical takeaway: if your objective is tail-risk control while retaining near-baseline throughput and avoiding LPM outliers, adaptive 0.63 is still reasonable. If your objective is strict minimum P99 in this exact workload, FCFS looks stronger and should be included as a production candidate.

## Related Figures

- [Adaptive vs FCFS P99 by threshold](loogle_63p_jain_concurrency_16_adaptive_vs_fcfs_p99_improvement.png)
- [Adaptive threshold metrics panel](loogle_63p_jain_concurrency_16_adaptive_metrics_by_threshold.png)
- [Main run Pareto plot](loogle_63p_jain_concurrency_16_pareto.png)
- [Cross-threshold report](loogle_63p_jain_concurrency_16_threshold_comparison_summary.md)

## Suggested Next Validation Steps

1. Run 3-5 seeds for each policy at n=50 and n=100, then compare median and IQR of P99 to reduce single-run variance.
2. Add a simple policy selection rule for deployment experiments: choose FCFS when minimizing absolute P99 is primary, choose adaptive when fairness-aware control and outlier suppression are primary.
3. Collect request-level fairness and violation-rate summaries per policy to quantify the fairness-latency tradeoff explicitly.