# LooGLE Jain Threshold Comparison Summary (0.60 vs 0.63 vs 0.65)

Generated on: 2026-04-21

## Data Sources

- J=0.60: `results/modal_grid_loogle_60p_jain_threshold/summary.csv`
- J=0.63: `results/modal_grid_20260421_185446/summary.csv`
- J=0.65: `results/modal_grid_loogle_65p_jain_threshold/summary.csv`

## Additional Plots Generated

- `docs/plots/loogle_63p_jain_concurrency_16/loogle_63p_jain_concurrency_16_adaptive_metrics_by_threshold.png`
- `docs/plots/loogle_63p_jain_concurrency_16/loogle_63p_jain_concurrency_16_adaptive_p99_pairwise_improvement.png`
- `docs/plots/loogle_63p_jain_concurrency_16/loogle_63p_jain_concurrency_16_adaptive_vs_fcfs_p99_improvement.png`

## Adaptive Rows Used For Cross-Threshold Comparison
```text
 jain_threshold        policy  request_count  success_rate  throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms                                                                output_file
         0.6000 adaptive_j060             25        1.0000                  8.1677     614.4844  175656.9264  results\modal_grid_20260421_161221\runs\adaptive_dlpm_r1.0_k1.0_n25.jsonl
         0.6000 adaptive_j060             50        1.0000                  9.2169    1001.7839    2566.0765  results\modal_grid_20260421_161221\runs\adaptive_dlpm_r1.0_k1.0_n50.jsonl
         0.6300 adaptive_dlpm             25        1.0000                  8.1676     573.0447   18220.3575  results\modal_grid_20260421_185446\runs\adaptive_dlpm_r1.0_k1.0_n25.jsonl
         0.6300 adaptive_dlpm             50        1.0000                  9.2169     698.1283    3274.9426  results\modal_grid_20260421_185446\runs\adaptive_dlpm_r1.0_k1.0_n50.jsonl
         0.6300 adaptive_dlpm            100        0.9987                  8.5200    1364.6796    6602.7925 results\modal_grid_20260421_185446\runs\adaptive_dlpm_r1.0_k1.0_n100.jsonl
         0.6500 adaptive_dlpm             25        0.9946                  7.9676     564.3558   24551.2034  results\modal_grid_20260421_150551\runs\adaptive_dlpm_r1.0_k1.0_n25.jsonl
         0.6500 adaptive_dlpm             50        1.0000                  9.2169     638.6352    1661.7851  results\modal_grid_20260421_150551\runs\adaptive_dlpm_r1.0_k1.0_n50.jsonl
```

## Pairwise Adaptive Improvements (common n only; positive latency improvement is better)
```text
 request_count  j063_vs_j065_p99_impr_pct  j065_vs_j060_p99_impr_pct  j063_vs_j060_p99_impr_pct  j063_vs_j065_p50_impr_pct  j065_vs_j060_p50_impr_pct  j063_vs_j060_p50_impr_pct  j063_vs_j065_thr_delta_pct  j065_vs_j060_thr_delta_pct  j063_vs_j060_thr_delta_pct
            25                      25.79                      86.02                      89.63                      -1.54                       8.16                       6.74                        2.51                       -2.45                       -0.00
            50                     -97.07                      35.24                     -27.62                      -9.32                      36.25                      30.31                       -0.00                       -0.00                       -0.00
```

## Adaptive vs Baseline Policies (within each threshold result set)
```text
jain_threshold  request_count baseline  ttft_p99_improvement_pct  ttft_p50_improvement_pct  throughput_improvement_pct
          0.60             25     dlpm                   -638.03                     46.25                       -0.00
          0.60             25     fcfs                   -507.24                     48.55                        0.00
          0.60             25      lpm                   -533.96                      9.74                       -0.00
          0.60             50     dlpm                     -2.99                     14.85                        0.00
          0.60             50     fcfs                     -8.96                     17.72                        0.00
          0.60             50      lpm                    -33.27                    -35.80                       -0.00
          0.63             25     dlpm                     37.03                     -3.96                        0.00
          0.63             25     fcfs                     13.70                    -28.99                       -0.00
          0.63             25      lpm                     39.88                     96.13                        0.00
          0.63             50     dlpm                     -5.35                     -3.59                       -0.00
          0.63             50     fcfs                    -27.01                    -24.89                       -0.00
          0.63             50      lpm                     97.74                     95.17                        1.31
          0.63            100     dlpm                     10.61                     -9.29                       -0.05
          0.63            100     fcfs                    -58.53                    -25.74                       -0.05
          0.63            100      lpm                     -9.46                     -0.66                       -0.05
          0.65             25     dlpm                     -3.15                     50.64                       -2.45
          0.65             25     fcfs                     15.13                     52.75                       -2.45
          0.65             25      lpm                     11.39                     17.11                       -2.45
          0.65             50     dlpm                     33.31                     45.71                        0.00
          0.65             50     fcfs                     29.44                     47.54                        0.00
          0.65             50      lpm                     13.69                     13.43                       -0.00
```

## Threshold Winner By Request Count (lowest adaptive P99)
```text
n=25: J=0.63 with adaptive P99=18220.36 ms
n=50: J=0.65 with adaptive P99=1661.79 ms
n=100: J=0.63 with adaptive P99=6602.79 ms
```

## Tail-Latency Spread Across Thresholds (common n)
```text
 request_count  min_p99_ms  max_p99_ms  spread_pct_of_min
            25    18220.36   175656.93             864.07
            50     1661.79     3274.94              97.07
```

## 0.63 Run Snapshot At n=100 (no direct 0.60/0.65 counterpart)
```text
       policy  success_rate  throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
         fcfs          1.00                    8.52      1085.28      4164.90
          lpm          1.00                    8.52      1355.72      6032.08
adaptive_dlpm          1.00                    8.52      1364.68      6602.79
         dlpm          1.00                    8.52      1248.69      7386.37
```

## Analysis Summary

1. Adaptive tail-latency winners on common request counts: n=25->J=0.63, n=50->J=0.65.
2. J=0.60 is highly unstable at n=25 in this sample: P99=175656.93 ms vs J=0.63 (18220.36 ms) and J=0.65 (24551.20 ms).
3. Throughput differences across adaptive thresholds are small (max spread across common n is 2.51%), so the primary tradeoff is latency tail behavior.
4. At n=100 there is only J=0.63 adaptive data in this comparison, so cross-threshold ranking at n=100 is not yet available.
5. Within the 0.63 n=100 policy snapshot, FCFS has the lowest P99; adaptive is better than static DLPM but trails FCFS and LPM.

## Suggested Next Steps

1. Repeat n=25 for each threshold with 3 to 5 seeds and compare median plus IQR of P99 before locking a threshold.
2. Add a fine-grained sweep around the current best point: J in {0.62, 0.63, 0.64, 0.65}.
3. Validate under deeper load (rate=2.0 and 3.0) with the same concurrency setting to test threshold robustness.
4. Add a guardrail experiment for J=0.60 (faster cutback on repeated Jain violations) to reduce heavy-tail risk.
5. If objective is pure tail minimization at n=100, run matched 0.60 and 0.65 experiments at n=100 to avoid one-sided conclusions.