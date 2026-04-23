# Benchmark Summary: modal_grid_20260422_191305

Rows: 24
Policies: adaptive_dlpm, dlpm, fcfs, lpm

## Policy Medians
```text
               throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
policy                                                         
adaptive_dlpm                 183.968    23465.975    30160.521
dlpm                          163.725    10765.483    19300.678
fcfs                          225.206     7084.107    14599.122
lpm                           218.245     7669.888    16333.704
```

## Policy Means
```text
               throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
policy                                                         
adaptive_dlpm                 178.775    24125.743    43413.114
dlpm                          192.537    15523.327    29057.984
fcfs                          225.288     5682.266    13458.459
lpm                           221.721     6734.854    15730.424
```

## Best Throughput Row Per Policy
```text
       policy  rate   k  request_count  throughput_tok_per_sec  ttft_p99_ms
adaptive_dlpm   1.0 0.5            100              219.242451 30174.896125
         dlpm   1.0 1.0            100              292.425349 16944.571750
         fcfs   1.0 0.5            100              300.248624 14573.528333
          lpm   1.0 0.5            100              299.981386 13695.054750
```

## Best (Lowest) TTFT P99 Row Per Policy
```text
       policy  rate   k  request_count  throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
adaptive_dlpm   0.5 1.0            100              150.303501  8002.851625 19226.490458
         dlpm   0.5 1.0            100              150.474594  1466.247500 11762.752709
         fcfs   0.5 1.0            100              150.502105   757.774500  9105.515542
          lpm   0.5 1.0            100              150.413097   774.050792  8954.313709
```

## High-Load (Max Rate) Median by Policy
```text
               throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
policy                                                         
adaptive_dlpm                 218.437    23465.975    30160.521
dlpm                          235.393    13570.880    30157.549
fcfs                          300.079     7719.875    14599.122
lpm                           292.988     8779.299    16333.704
```

## Severe TTFT P99 Outliers (> 10,000 ms)
```text
       policy  rate   k  request_count  ttft_p99_ms                                                                output_file
adaptive_dlpm   0.5 0.5            100 94104.922250 results/modal_grid_20260422_191305/runs/adaptive_dlpm_r0.5_k0.5_n100.jsonl
adaptive_dlpm   0.5 1.0            100 19226.490458 results/modal_grid_20260422_191305/runs/adaptive_dlpm_r0.5_k1.0_n100.jsonl
adaptive_dlpm   1.0 0.5            100 30174.896125 results/modal_grid_20260422_191305/runs/adaptive_dlpm_r1.0_k0.5_n100.jsonl
adaptive_dlpm   1.0 1.0            100 30146.145958 results/modal_grid_20260422_191305/runs/adaptive_dlpm_r1.0_k1.0_n100.jsonl
         fcfs   0.5 0.5            100 15530.075792          results/modal_grid_20260422_191305/runs/fcfs_r0.5_k0.5_n100.jsonl
         fcfs   1.0 0.5            100 14573.528333          results/modal_grid_20260422_191305/runs/fcfs_r1.0_k0.5_n100.jsonl
         fcfs   1.0 1.0            100 14624.715000          results/modal_grid_20260422_191305/runs/fcfs_r1.0_k1.0_n100.jsonl
          lpm   0.5 0.5            100 21299.974583           results/modal_grid_20260422_191305/runs/lpm_r0.5_k0.5_n100.jsonl
          lpm   1.0 0.5            100 13695.054750           results/modal_grid_20260422_191305/runs/lpm_r1.0_k0.5_n100.jsonl
          lpm   1.0 1.0            100 18972.352958           results/modal_grid_20260422_191305/runs/lpm_r1.0_k1.0_n100.jsonl
         dlpm   0.5 0.5            100 19128.282417    results/modal_grid_20260422_191305/runs/dlpm_q1200_r0.5_k0.5_n100.jsonl
         dlpm   0.5 1.0            100 11762.752709    results/modal_grid_20260422_191305/runs/dlpm_q1200_r0.5_k1.0_n100.jsonl
         dlpm   1.0 0.5            100 17632.956000    results/modal_grid_20260422_191305/runs/dlpm_q1200_r1.0_k0.5_n100.jsonl
         dlpm   1.0 1.0            100 16944.571750    results/modal_grid_20260422_191305/runs/dlpm_q1200_r1.0_k1.0_n100.jsonl
         dlpm   0.5 0.5            100 19473.074041    results/modal_grid_20260422_191305/runs/dlpm_q4000_r0.5_k0.5_n100.jsonl
         dlpm   0.5 1.0            100 11789.886291    results/modal_grid_20260422_191305/runs/dlpm_q4000_r0.5_k1.0_n100.jsonl
         dlpm   1.0 0.5            100 67268.551167    results/modal_grid_20260422_191305/runs/dlpm_q4000_r1.0_k0.5_n100.jsonl
         dlpm   1.0 1.0            100 17660.125208    results/modal_grid_20260422_191305/runs/dlpm_q4000_r1.0_k1.0_n100.jsonl
         dlpm   0.5 0.5            100 39250.971625    results/modal_grid_20260422_191305/runs/dlpm_q8000_r0.5_k0.5_n100.jsonl
         dlpm   0.5 1.0            100 41741.616583    results/modal_grid_20260422_191305/runs/dlpm_q8000_r0.5_k1.0_n100.jsonl
         dlpm   1.0 0.5            100 42654.972292    results/modal_grid_20260422_191305/runs/dlpm_q8000_r1.0_k0.5_n100.jsonl
         dlpm   1.0 1.0            100 43388.053833    results/modal_grid_20260422_191305/runs/dlpm_q8000_r1.0_k1.0_n100.jsonl
```

## Request-Level Telemetry Coverage
```text
total_request_rows: 6096
rows_with_Q_at_scheduling: 6096
rows_with_jain_control: 6096
rows_with_aimd_violated=true: 100
```

## Adaptive DLPM Median Q_at_scheduling
```text
adaptive_dlpm: 4500.00
```

## Adaptive AIMD Trace Coverage
```text
adaptive_runs_found: 4
one trace PNG is generated for each adaptive run
```
