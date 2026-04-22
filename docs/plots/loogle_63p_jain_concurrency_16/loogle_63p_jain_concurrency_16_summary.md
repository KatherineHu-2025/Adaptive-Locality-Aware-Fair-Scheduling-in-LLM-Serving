# Benchmark Summary: modal_grid_20260421_185446

Rows: 12
Policies: adaptive_dlpm, dlpm, fcfs, lpm

## Policy Medians
```text
               throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
policy                                                         
adaptive_dlpm                   8.520      698.128     6602.793
dlpm                            8.524      673.917     7386.373
fcfs                            8.524      558.975     4164.902
lpm                             8.524    14440.707    30307.517
```

## Policy Means
```text
               throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
policy                                                         
adaptive_dlpm                   8.635      878.618     9366.031
dlpm                            8.636      824.613    13142.990
fcfs                            8.636      696.172     9285.712
lpm                             8.597    10200.163    60488.877
```

## Best Throughput Row Per Policy
```text
       policy  rate   k  request_count  throughput_tok_per_sec  ttft_p99_ms
adaptive_dlpm   1.0 1.0             50                9.216925    3274.9426
         dlpm   1.0 1.0             50                9.216979    3108.5317
         fcfs   1.0 1.0             50                9.216926    2578.4043
          lpm   1.0 1.0             50                9.097646  145127.0359
```

## Best (Lowest) TTFT P99 Row Per Policy
```text
       policy  rate   k  request_count  throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
adaptive_dlpm   1.0 1.0             50                9.216925     698.1283    3274.9426
         dlpm   1.0 1.0             50                9.216979     673.9166    3108.5317
         fcfs   1.0 1.0             50                9.216926     558.9755    2578.4043
          lpm   1.0 1.0            100                8.524475    1355.7207    6032.0794
```

## High-Load (Max Rate) Median by Policy
```text
               throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
policy                                                         
adaptive_dlpm                   8.520      698.128     6602.793
dlpm                            8.524      673.917     7386.373
fcfs                            8.524      558.975     4164.902
lpm                             8.524    14440.707    30307.517
```

## Severe TTFT P99 Outliers (> 10,000 ms)
```text
       policy  rate   k  request_count  ttft_p99_ms                                                               output_file
adaptive_dlpm   1.0 1.0             25   18220.3575 results\modal_grid_20260421_185446\runs\adaptive_dlpm_r1.0_k1.0_n25.jsonl
         dlpm   1.0 1.0             25   28934.0651    results\modal_grid_20260421_185446\runs\dlpm_q4000_r1.0_k1.0_n25.jsonl
         fcfs   1.0 1.0             25   21113.8315          results\modal_grid_20260421_185446\runs\fcfs_r1.0_k1.0_n25.jsonl
          lpm   1.0 1.0             25   30307.5170           results\modal_grid_20260421_185446\runs\lpm_r1.0_k1.0_n25.jsonl
          lpm   1.0 1.0             50  145127.0359           results\modal_grid_20260421_185446\runs\lpm_r1.0_k1.0_n50.jsonl
```

## Request-Level Telemetry Coverage
```text
total_request_rows: 5460
rows_with_Q_at_scheduling: 5459
rows_with_jain_control: 5459
rows_with_aimd_violated=true: 709
```

## Adaptive DLPM Median Q_at_scheduling
```text
adaptive_dlpm: 1700.00
```

## Adaptive AIMD Trace Coverage
```text
adaptive_runs_found: 3
one trace PNG is generated for each adaptive run
```
