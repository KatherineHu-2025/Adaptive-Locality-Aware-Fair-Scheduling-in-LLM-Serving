# Benchmark Summary: modal_grid_20260425_011533

Rows: 6
Policies: adaptive_dlpm, dlpm_q1200, dlpm_q4000, dlpm_q8000, fcfs, lpm

## Policy Medians
```text
               throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
policy                                                         
adaptive_dlpm                 767.085    14271.297    28910.292
dlpm_q1200                    492.019    47055.759   117528.508
dlpm_q4000                    649.926    30912.356    52470.601
dlpm_q8000                    516.756    46894.787    95601.998
fcfs                          598.315    34366.779    61017.357
lpm                           712.098    22306.240    40173.933
```

## Policy Means
```text
               throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
policy                                                         
adaptive_dlpm                 767.085    14271.297    28910.292
dlpm_q1200                    492.019    47055.759   117528.508
dlpm_q4000                    649.926    30912.356    52470.601
dlpm_q8000                    516.756    46894.787    95601.998
fcfs                          598.315    34366.779    61017.357
lpm                           712.098    22306.240    40173.933
```

## Best Throughput Row Per Policy
```text
       policy  rate   k  request_count  throughput_tok_per_sec   ttft_p99_ms
adaptive_dlpm   1.0 1.0              0              767.084662  28910.292167
   dlpm_q1200   1.0 1.0              0              492.018818 117528.508375
   dlpm_q4000   1.0 1.0              0              649.926313  52470.600792
   dlpm_q8000   1.0 1.0              0              516.755623  95601.997875
         fcfs   1.0 1.0              0              598.315459  61017.356750
          lpm   1.0 1.0              0              712.098207  40173.932958
```

## Best (Lowest) TTFT P99 Row Per Policy
```text
       policy  rate   k  request_count  throughput_tok_per_sec  ttft_p50_ms   ttft_p99_ms
adaptive_dlpm   1.0 1.0              0              767.084662 14271.296833  28910.292167
   dlpm_q1200   1.0 1.0              0              492.018818 47055.759458 117528.508375
   dlpm_q4000   1.0 1.0              0              649.926313 30912.355958  52470.600792
   dlpm_q8000   1.0 1.0              0              516.755623 46894.787042  95601.997875
         fcfs   1.0 1.0              0              598.315459 34366.778583  61017.356750
          lpm   1.0 1.0              0              712.098207 22306.239875  40173.932958
```

## High-Load (Max Rate) Median by Policy
```text
               throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
policy                                                         
adaptive_dlpm                 767.085    14271.297    28910.292
dlpm_q1200                    492.019    47055.759   117528.508
dlpm_q4000                    649.926    30912.356    52470.601
dlpm_q8000                    516.756    46894.787    95601.998
fcfs                          598.315    34366.779    61017.357
lpm                           712.098    22306.240    40173.933
```

## Severe TTFT P99 Outliers (> 10,000 ms)
```text
       policy  rate   k  request_count   ttft_p99_ms                                                           output_file
adaptive_dlpm   1.0 1.0              0  28910.292167 results/modal_grid_20260425_011533/runs/adaptive_dlpm_misbehave.jsonl
          lpm   1.0 1.0              0  40173.932958           results/modal_grid_20260425_011533/runs/lpm_misbehave.jsonl
   dlpm_q1200   1.0 1.0              0 117528.508375    results/modal_grid_20260425_011533/runs/dlpm_q1200_misbehave.jsonl
   dlpm_q4000   1.0 1.0              0  52470.600792    results/modal_grid_20260425_011533/runs/dlpm_q4000_misbehave.jsonl
   dlpm_q8000   1.0 1.0              0  95601.997875    results/modal_grid_20260425_011533/runs/dlpm_q8000_misbehave.jsonl
         fcfs   1.0 1.0              0  61017.356750          results/modal_grid_20260425_011533/runs/fcfs_misbehave.jsonl
```

## Request-Level Telemetry Coverage
```text
total_request_rows: 12726
rows_with_Q_at_scheduling: 12726
rows_with_jain_control: 12726
rows_with_aimd_violated=true: 851
```

## Adaptive DLPM Median Q_at_scheduling
```text
adaptive_dlpm: 2200.00
```

## Adaptive AIMD Trace Coverage
```text
adaptive_runs_found: 1
one trace PNG is generated for each adaptive run
```
