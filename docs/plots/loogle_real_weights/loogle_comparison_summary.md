# Benchmark Summary: loogle_real_weights_comparison

Rows: 3
Policies: adaptive_dlpm, fcfs, lpm

## Policy Medians
```text
               throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
policy                                                         
adaptive_dlpm                   0.977     3941.842    19018.109
fcfs                            0.969     3871.038    24963.375
lpm                             0.995     3110.169    16863.322
```

## Policy Means
```text
               throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
policy                                                         
adaptive_dlpm                   0.977     3941.842    19018.109
fcfs                            0.969     3871.038    24963.375
lpm                             0.995     3110.169    16863.322
```

## Best Throughput Row Per Policy
```text
       policy  rate   k  request_count  throughput_tok_per_sec  ttft_p99_ms
adaptive_dlpm   1.0 1.0             50                0.976581 19018.108750
         fcfs   1.0 1.0             50                0.969285 24963.375042
          lpm   1.0 1.0             50                0.995455 16863.321750
```

## Best (Lowest) TTFT P99 Row Per Policy
```text
       policy  rate   k  request_count  throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
adaptive_dlpm   1.0 1.0             50                0.976581  3941.841666 19018.108750
         fcfs   1.0 1.0             50                0.969285  3871.038458 24963.375042
          lpm   1.0 1.0             50                0.995455  3110.169291 16863.321750
```

## High-Load (Max Rate) Median by Policy
```text
               throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
policy                                                         
adaptive_dlpm                   0.977     3941.842    19018.109
fcfs                            0.969     3871.038    24963.375
lpm                             0.995     3110.169    16863.322
```

## Severe TTFT P99 Outliers (> 10,000 ms)
```text
       policy  rate   k  request_count  ttft_p99_ms                                                               output_file
adaptive_dlpm   1.0 1.0             50 19018.108750 results/modal_grid_20260415_184759/runs/adaptive_dlpm_r1.0_k1.0_n50.jsonl
          lpm   1.0 1.0             50 16863.321750           results/modal_grid_20260415_191004/runs/lpm_r1.0_k1.0_n50.jsonl
         fcfs   1.0 1.0             50 24963.375042          results/modal_grid_20260415_191004/runs/fcfs_r1.0_k1.0_n50.jsonl
```
