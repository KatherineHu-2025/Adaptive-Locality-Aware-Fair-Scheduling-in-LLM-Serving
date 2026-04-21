# LooGLE 0.60 Jain Threshold Improvement Summary

This compares baseline policies from `modal_grid_20260419_160306` with adaptive at three thresholds: original (`J=0.75`), `J=0.65`, and new `J=0.60`.

Combined result set: `results/modal_grid_loogle_60p_jain_threshold/summary.csv`
Output folder: `docs/plots/loogle_60p_jain_threshold/`

## New Plots Generated

- `loogle_60p_jain_threshold_adaptive_jain_sweep.png`: 2x2 panel for adaptive-only P50/P99/throughput/success across `J=0.75/0.65/0.60` by `n`.
- `loogle_60p_jain_threshold_adaptive_pairwise_p99_improvement.png`: pairwise P99 improvements among adaptive thresholds.
- Standard merged plots (throughput/p99/pareto/histograms) from `plot_benchmark_result.py`.

## Adaptive Head-to-Head (positive improvement means lower TTFT is better)
```text
 request_count  j065_vs_j075_p99_impr_pct  j060_vs_j075_p99_impr_pct  j060_vs_j065_p99_impr_pct  j065_vs_j075_p50_impr_pct  j060_vs_j075_p50_impr_pct  j060_vs_j065_p50_impr_pct  j065_vs_j075_thr_delta_pct  j060_vs_j075_thr_delta_pct  j060_vs_j065_thr_delta_pct
            25                      22.03                    -457.84                    -615.47                      55.79                      51.87                      -8.88                       -2.45                       -0.00                        2.51
            50                      42.60                      11.36                     -54.42                      48.27                      18.86                     -56.86                        0.00                        0.00                        0.00
```

## Adaptive vs Baseline Policies
```text
     adaptive  request_count baseline  ttft_p99_improvement_pct  ttft_p50_improvement_pct  throughput_improvement_pct
adaptive_j075             25     fcfs                     -8.86                     -6.88                        0.00
adaptive_j075             25     dlpm                    -32.30                    -11.66                       -0.00
adaptive_j075             25      lpm                    -13.65                    -87.51                       -0.00
adaptive_j075             50     fcfs                    -22.93                     -1.41                        0.00
adaptive_j075             50     dlpm                    -16.19                     -4.95                        0.00
adaptive_j075             50      lpm                    -50.36                    -67.37                       -0.00
adaptive_j065             25     fcfs                     15.13                     52.75                       -2.45
adaptive_j065             25     dlpm                     -3.15                     50.64                       -2.45
adaptive_j065             25      lpm                     11.39                     17.11                       -2.45
adaptive_j065             50     fcfs                     29.44                     47.54                        0.00
adaptive_j065             50     dlpm                     33.31                     45.71                        0.00
adaptive_j065             50      lpm                     13.69                     13.43                       -0.00
adaptive_j060             25     fcfs                   -507.24                     48.55                        0.00
adaptive_j060             25     dlpm                   -638.03                     46.25                       -0.00
adaptive_j060             25      lpm                   -533.96                      9.74                       -0.00
adaptive_j060             50     fcfs                     -8.96                     17.72                        0.00
adaptive_j060             50     dlpm                     -2.99                     14.85                        0.00
adaptive_j060             50      lpm                    -33.27                    -35.80                       -0.00
```

## Key Findings

1. At n=50, J=0.65 is best among adaptive variants for tail latency: +42.60% vs J=0.75 and +54.42% better than J=0.60.
2. At n=50, J=0.60 still improves over original J=0.75 in P99 (+11.36%), but regresses vs J=0.65.
3. At n=25, J=0.60 is unstable in tail behavior (very large P99 regression vs J=0.75: -457.84%).
4. Throughput differences among adaptive variants are near-zero at n=50; most differences are in latency/tail behavior.
5. For this slice, J=0.65 remains the best operating point; J=0.60 appears too relaxed for consistent tail control.

## Recommended Next Steps

1. Re-run J=0.60 at n=25 with 3 to 5 seeds and use median/IQR before concluding on tail behavior.
2. Evaluate a narrower sweep around the apparent sweet spot: J in {0.62, 0.65, 0.68}.
3. Run higher-rate checks (rate=2.0,3.0) to validate whether J=0.65 remains best under deeper queues.
4. If J=0.60 keeps producing occasional huge tails, add guardrails (lower Q cap increase rate or tighter violation response).