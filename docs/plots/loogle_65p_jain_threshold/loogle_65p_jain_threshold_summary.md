# Benchmark Summary: modal_grid_loogle_65p_jain_threshold

Rows: 8
Policies: adaptive_dlpm, dlpm, fcfs, lpm

## Policy Medians
```text
               throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
policy                                                         
adaptive_dlpm                   8.592      601.495    13106.494
dlpm                            8.692     1159.848    13146.294
fcfs                            8.692     1205.946    15641.085
lpm                             8.692      709.251    14816.738
```

## Policy Means
```text
               throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
policy                                                         
adaptive_dlpm                   8.592      601.495    13106.494
dlpm                            8.692     1159.848    13146.294
fcfs                            8.692     1205.946    15641.085
lpm                             8.692      709.251    14816.738
```

## Best Throughput Row Per Policy
```text
       policy  rate   k  request_count  throughput_tok_per_sec  ttft_p99_ms
adaptive_dlpm   1.0 1.0             50                9.216938    1661.7851
         dlpm   1.0 1.0             50                9.216864    2491.6563
         fcfs   1.0 1.0             50                9.216886    2355.0578
          lpm   1.0 1.0             50                9.217009    1925.4693
```

## Best (Lowest) TTFT P99 Row Per Policy
```text
       policy  rate   k  request_count  throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
adaptive_dlpm   1.0 1.0             50                9.216938     638.6352    1661.7851
         dlpm   1.0 1.0             50                9.216864    1176.4255    2491.6563
         fcfs   1.0 1.0             50                9.216886    1217.4599    2355.0578
          lpm   1.0 1.0             50                9.217009     737.6895    1925.4693
```

## High-Load (Max Rate) Median by Policy
```text
               throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
policy                                                         
adaptive_dlpm                   8.592      601.495    13106.494
dlpm                            8.692     1159.848    13146.294
fcfs                            8.692     1205.946    15641.085
lpm                             8.692      709.251    14816.738
```

## Severe TTFT P99 Outliers (> 10,000 ms)
```text
       policy  rate   k  request_count  ttft_p99_ms                                                               output_file
adaptive_dlpm   1.0 1.0             25   24551.2034 results\modal_grid_20260421_150551\runs\adaptive_dlpm_r1.0_k1.0_n25.jsonl
         dlpm   1.0 1.0             25   23800.9311    results\modal_grid_20260419_160306\runs\dlpm_q4000_r1.0_k1.0_n25.jsonl
         fcfs   1.0 1.0             25   28927.1122          results\modal_grid_20260419_160306\runs\fcfs_r1.0_k1.0_n25.jsonl
          lpm   1.0 1.0             25   27708.0077           results\modal_grid_20260419_160306\runs\lpm_r1.0_k1.0_n25.jsonl
```

## Request-Level Telemetry Coverage
```text
total_request_rows: 2276
rows_with_Q_at_scheduling: 2275
rows_with_jain_control: 2275
rows_with_aimd_violated=true: 467
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
