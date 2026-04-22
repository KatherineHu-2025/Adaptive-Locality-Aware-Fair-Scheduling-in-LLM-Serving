# Benchmark Summary: modal_grid_20260421_171114

Rows: 8
Policies: adaptive_dlpm, dlpm, fcfs, lpm

## Policy Medians
```text
               throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
policy                                                         
adaptive_dlpm                   8.692      692.935    10446.177
dlpm                            8.068      596.166   200897.868
fcfs                            8.692      245.009     8335.444
lpm                             8.692     1611.986    20558.402
```

## Policy Means
```text
               throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
policy                                                         
adaptive_dlpm                   8.692      692.935    10446.177
dlpm                            8.068      596.166   200897.868
fcfs                            8.692      245.009     8335.444
lpm                             8.692     1611.986    20558.402
```

## Best Throughput Row Per Policy
```text
       policy  rate   k  request_count  throughput_tok_per_sec  ttft_p99_ms
adaptive_dlpm   1.0 1.0             50                9.216941    3418.7289
         dlpm   1.0 1.0             25                8.167795   19557.9798
         fcfs   1.0 1.0             50                9.216914    2341.1547
          lpm   1.0 1.0             50                9.217041    3471.0652
```

## Best (Lowest) TTFT P99 Row Per Policy
```text
       policy  rate   k  request_count  throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
adaptive_dlpm   1.0 1.0             50                9.216941     784.1572    3418.7289
         dlpm   1.0 1.0             25                8.167795     398.5576   19557.9798
         fcfs   1.0 1.0             50                9.216914     265.0804    2341.1547
          lpm   1.0 1.0             50                9.217041     711.6823    3471.0652
```

## High-Load (Max Rate) Median by Policy
```text
               throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
policy                                                         
adaptive_dlpm                   8.692      692.935    10446.177
dlpm                            8.068      596.166   200897.868
fcfs                            8.692      245.009     8335.444
lpm                             8.692     1611.986    20558.402
```

## Severe TTFT P99 Outliers (> 10,000 ms)
```text
       policy  rate   k  request_count  ttft_p99_ms                                                               output_file
adaptive_dlpm   1.0 1.0             25   17473.6248 results\modal_grid_20260421_171114\runs\adaptive_dlpm_r1.0_k1.0_n25.jsonl
         dlpm   1.0 1.0             25   19557.9798    results\modal_grid_20260421_171114\runs\dlpm_q4000_r1.0_k1.0_n25.jsonl
         dlpm   1.0 1.0             50  382237.7561    results\modal_grid_20260421_171114\runs\dlpm_q4000_r1.0_k1.0_n50.jsonl
         fcfs   1.0 1.0             25   14329.7339          results\modal_grid_20260421_171114\runs\fcfs_r1.0_k1.0_n25.jsonl
          lpm   1.0 1.0             25   37645.7386           results\modal_grid_20260421_171114\runs\lpm_r1.0_k1.0_n25.jsonl
```

## Request-Level Telemetry Coverage
```text
total_request_rows: 2276
rows_with_Q_at_scheduling: 2276
rows_with_jain_control: 2276
rows_with_aimd_violated=true: 468
```

## Adaptive DLPM Median Q_at_scheduling
```text
adaptive_dlpm: 1200.00
```

## Adaptive AIMD Trace Coverage
```text
adaptive_runs_found: 2
one trace PNG is generated for each adaptive run
```
