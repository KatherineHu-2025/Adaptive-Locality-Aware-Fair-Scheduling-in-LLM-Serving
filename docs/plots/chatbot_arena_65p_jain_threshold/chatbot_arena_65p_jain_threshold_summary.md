# Benchmark Summary: modal_grid_20260421_192628

Rows: 24
Policies: adaptive_dlpm, dlpm, fcfs, lpm

## Policy Medians
```text
               throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
policy                                                         
adaptive_dlpm                 163.872    49026.223    68789.979
dlpm                          195.189    40305.278    58253.544
fcfs                          168.010    48904.488    67791.718
lpm                           249.509    30268.034    44230.225
```

## Policy Means
```text
               throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
policy                                                         
adaptive_dlpm                 146.306    50470.453   113074.834
dlpm                          210.784    37255.753    76626.445
fcfs                          166.224    47958.532    66575.578
lpm                           210.883    33393.553    92370.340
```

## Best Throughput Row Per Policy
```text
       policy  rate   k  request_count  throughput_tok_per_sec  ttft_p99_ms
adaptive_dlpm   2.0 1.0            100              176.608923 59650.617042
         dlpm   4.0 1.0            100              328.576007 32267.898375
         fcfs   2.0 1.0            100              176.312821 60562.132958
          lpm   4.0 0.5            100              257.051912 43144.785125
```

## Best (Lowest) TTFT P99 Row Per Policy
```text
       policy  rate   k  request_count  throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
adaptive_dlpm   2.0 1.0            100              176.608923 41283.726458 59650.617042
         dlpm   2.0 1.0            100              315.386893 17179.539542 26477.286959
         fcfs   2.0 1.0            100              176.312821 41244.641333 60562.132958
          lpm   2.0 1.0            100              250.367960 25216.161500 38745.220541
```

## High-Load (Max Rate) Median by Policy
```text
               throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
policy                                                         
adaptive_dlpm                 128.449    54532.752   161334.079
dlpm                          195.921    40739.858    58669.671
fcfs                          168.010    49862.705    67791.718
lpm                           252.851    30268.034    44230.225
```

## Severe TTFT P99 Outliers (> 10,000 ms)
```text
       policy  rate   k  request_count   ttft_p99_ms                                                                output_file
adaptive_dlpm   2.0 0.5            100  69980.562250 results/modal_grid_20260421_192628/runs/adaptive_dlpm_r2.0_k0.5_n100.jsonl
adaptive_dlpm   2.0 1.0            100  59650.617042 results/modal_grid_20260421_192628/runs/adaptive_dlpm_r2.0_k1.0_n100.jsonl
adaptive_dlpm   4.0 0.5            100  67599.394750 results/modal_grid_20260421_192628/runs/adaptive_dlpm_r4.0_k0.5_n100.jsonl
adaptive_dlpm   4.0 1.0            100 255068.762708 results/modal_grid_20260421_192628/runs/adaptive_dlpm_r4.0_k1.0_n100.jsonl
          lpm   2.0 0.5            100 242275.689208           results/modal_grid_20260421_192628/runs/lpm_r2.0_k0.5_n100.jsonl
          lpm   2.0 1.0            100  38745.220541           results/modal_grid_20260421_192628/runs/lpm_r2.0_k1.0_n100.jsonl
          lpm   4.0 0.5            100  43144.785125           results/modal_grid_20260421_192628/runs/lpm_r4.0_k0.5_n100.jsonl
          lpm   4.0 1.0            100  45315.665250           results/modal_grid_20260421_192628/runs/lpm_r4.0_k1.0_n100.jsonl
         fcfs   2.0 0.5            100  70156.743166          results/modal_grid_20260421_192628/runs/fcfs_r2.0_k0.5_n100.jsonl
         fcfs   2.0 1.0            100  60562.132958          results/modal_grid_20260421_192628/runs/fcfs_r2.0_k1.0_n100.jsonl
         fcfs   4.0 0.5            100  65628.365459          results/modal_grid_20260421_192628/runs/fcfs_r4.0_k0.5_n100.jsonl
         fcfs   4.0 1.0            100  69955.070709          results/modal_grid_20260421_192628/runs/fcfs_r4.0_k1.0_n100.jsonl
         dlpm   2.0 0.5            100  38849.011500    results/modal_grid_20260421_192628/runs/dlpm_q1200_r2.0_k0.5_n100.jsonl
         dlpm   2.0 1.0            100  26477.286959    results/modal_grid_20260421_192628/runs/dlpm_q1200_r2.0_k1.0_n100.jsonl
         dlpm   4.0 0.5            100  32146.684125    results/modal_grid_20260421_192628/runs/dlpm_q1200_r4.0_k0.5_n100.jsonl
         dlpm   4.0 1.0            100  32267.898375    results/modal_grid_20260421_192628/runs/dlpm_q1200_r4.0_k1.0_n100.jsonl
         dlpm   2.0 0.5            100 173139.055292    results/modal_grid_20260421_192628/runs/dlpm_q4000_r2.0_k0.5_n100.jsonl
         dlpm   2.0 1.0            100  57854.264792    results/modal_grid_20260421_192628/runs/dlpm_q4000_r2.0_k1.0_n100.jsonl
         dlpm   4.0 0.5            100 256610.094459    results/modal_grid_20260421_192628/runs/dlpm_q4000_r4.0_k0.5_n100.jsonl
         dlpm   4.0 1.0            100  65320.417625    results/modal_grid_20260421_192628/runs/dlpm_q4000_r4.0_k1.0_n100.jsonl
         dlpm   2.0 0.5            100  67060.909209    results/modal_grid_20260421_192628/runs/dlpm_q8000_r2.0_k0.5_n100.jsonl
         dlpm   2.0 1.0            100  52452.380167    results/modal_grid_20260421_192628/runs/dlpm_q8000_r2.0_k1.0_n100.jsonl
         dlpm   4.0 0.5            100  58686.520083    results/modal_grid_20260421_192628/runs/dlpm_q8000_r4.0_k0.5_n100.jsonl
         dlpm   4.0 1.0            100  58652.822875    results/modal_grid_20260421_192628/runs/dlpm_q8000_r4.0_k1.0_n100.jsonl
```

## Request-Level Telemetry Coverage
```text
total_request_rows: 6096
rows_with_Q_at_scheduling: 6095
rows_with_jain_control: 6095
rows_with_aimd_violated=true: 917
```

## Adaptive DLPM Median Q_at_scheduling
```text
adaptive_dlpm: 1200.00
```

## Adaptive AIMD Trace Coverage
```text
adaptive_runs_found: 4
one trace PNG is generated for each adaptive run
```
