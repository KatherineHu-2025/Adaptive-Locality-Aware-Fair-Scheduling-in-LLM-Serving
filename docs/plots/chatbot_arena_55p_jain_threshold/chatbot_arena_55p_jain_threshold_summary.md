# Benchmark Summary: modal_grid_20260422_171534

Rows: 24
Policies: adaptive_dlpm, dlpm, fcfs, lpm

## Policy Medians
```text
               throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
policy                                                         
adaptive_dlpm                 147.500    33791.811    51599.274
dlpm                          213.600    10518.361    18230.297
fcfs                          146.008    24719.380    35387.863
lpm                           162.362    20701.873    28854.397
```

## Policy Means
```text
               throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
policy                                                         
adaptive_dlpm                 135.073    30924.597    72335.955
dlpm                          217.395     8734.481    17757.622
fcfs                          154.259    29875.340    81520.805
lpm                           172.263    18501.050    35223.346
```

## Best Throughput Row Per Policy
```text
       policy  rate   k  request_count  throughput_tok_per_sec  ttft_p99_ms
adaptive_dlpm   1.0 0.5            100              158.220269 50029.672417
         dlpm   1.0 1.0            100              291.701772 16931.703334
         fcfs   1.0 1.0            100              238.401671 26661.735667
          lpm   1.0 0.5            100              214.013068 30822.542583
```

## Best (Lowest) TTFT P99 Row Per Policy
```text
       policy  rate   k  request_count  throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
adaptive_dlpm   0.5 0.5            100              138.346885 30962.001000 42032.061250
         dlpm   0.5 1.0            100              150.494608  1687.526708 11598.229917
         fcfs   1.0 1.0            100              238.401671 20160.964542 26661.735667
          lpm   0.5 1.0            100              150.314635  8083.597500 19525.395500
```

## High-Load (Max Rate) Median by Policy
```text
               throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
policy                                                         
adaptive_dlpm                 157.436    36882.104    51599.274
dlpm                          285.185    11038.774    18230.297
fcfs                          162.509    36495.857   127653.747
lpm                           194.199    24482.160    47240.869
```

## Severe TTFT P99 Outliers (> 10,000 ms)
```text
       policy  rate   k  request_count   ttft_p99_ms                                                                output_file
adaptive_dlpm   0.5 0.5            100  42032.061250 results/modal_grid_20260422_171534/runs/adaptive_dlpm_r0.5_k0.5_n100.jsonl
adaptive_dlpm   0.5 1.0            100 144113.212458 results/modal_grid_20260422_171534/runs/adaptive_dlpm_r0.5_k1.0_n100.jsonl
adaptive_dlpm   1.0 0.5            100  50029.672417 results/modal_grid_20260422_171534/runs/adaptive_dlpm_r1.0_k0.5_n100.jsonl
adaptive_dlpm   1.0 1.0            100  53168.875000 results/modal_grid_20260422_171534/runs/adaptive_dlpm_r1.0_k1.0_n100.jsonl
         fcfs   0.5 0.5            100  40836.097000          results/modal_grid_20260422_171534/runs/fcfs_r0.5_k0.5_n100.jsonl
         fcfs   0.5 1.0            100  29939.628083          results/modal_grid_20260422_171534/runs/fcfs_r0.5_k1.0_n100.jsonl
         fcfs   1.0 0.5            100 228645.758417          results/modal_grid_20260422_171534/runs/fcfs_r1.0_k0.5_n100.jsonl
         fcfs   1.0 1.0            100  26661.735667          results/modal_grid_20260422_171534/runs/fcfs_r1.0_k1.0_n100.jsonl
          lpm   0.5 0.5            100  26886.251958           results/modal_grid_20260422_171534/runs/lpm_r0.5_k0.5_n100.jsonl
          lpm   0.5 1.0            100  19525.395500           results/modal_grid_20260422_171534/runs/lpm_r0.5_k1.0_n100.jsonl
          lpm   1.0 0.5            100  30822.542583           results/modal_grid_20260422_171534/runs/lpm_r1.0_k0.5_n100.jsonl
          lpm   1.0 1.0            100  63659.195084           results/modal_grid_20260422_171534/runs/lpm_r1.0_k1.0_n100.jsonl
         dlpm   0.5 0.5            100  23485.702000    results/modal_grid_20260422_171534/runs/dlpm_q1200_r0.5_k0.5_n100.jsonl
         dlpm   0.5 1.0            100  15810.497541    results/modal_grid_20260422_171534/runs/dlpm_q1200_r0.5_k1.0_n100.jsonl
         dlpm   1.0 0.5            100  18877.458084    results/modal_grid_20260422_171534/runs/dlpm_q1200_r1.0_k0.5_n100.jsonl
         dlpm   1.0 1.0            100  18922.977042    results/modal_grid_20260422_171534/runs/dlpm_q1200_r1.0_k1.0_n100.jsonl
         dlpm   0.5 0.5            100  20582.146625    results/modal_grid_20260422_171534/runs/dlpm_q4000_r0.5_k0.5_n100.jsonl
         dlpm   0.5 1.0            100  13633.901667    results/modal_grid_20260422_171534/runs/dlpm_q4000_r0.5_k1.0_n100.jsonl
         dlpm   1.0 0.5            100  18718.789084    results/modal_grid_20260422_171534/runs/dlpm_q4000_r1.0_k0.5_n100.jsonl
         dlpm   1.0 1.0            100  16931.703334    results/modal_grid_20260422_171534/runs/dlpm_q4000_r1.0_k1.0_n100.jsonl
         dlpm   0.5 0.5            100  19545.469250    results/modal_grid_20260422_171534/runs/dlpm_q8000_r0.5_k0.5_n100.jsonl
         dlpm   0.5 1.0            100  11598.229917    results/modal_grid_20260422_171534/runs/dlpm_q8000_r0.5_k1.0_n100.jsonl
         dlpm   1.0 0.5            100  17242.778959    results/modal_grid_20260422_171534/runs/dlpm_q8000_r1.0_k0.5_n100.jsonl
         dlpm   1.0 1.0            100  17741.804875    results/modal_grid_20260422_171534/runs/dlpm_q8000_r1.0_k1.0_n100.jsonl
```

## Request-Level Telemetry Coverage
```text
total_request_rows: 6096
rows_with_Q_at_scheduling: 6096
rows_with_jain_control: 6096
rows_with_aimd_violated=true: 150
```

## Adaptive DLPM Median Q_at_scheduling
```text
adaptive_dlpm: 3500.00
```

## Adaptive AIMD Trace Coverage
```text
adaptive_runs_found: 4
one trace PNG is generated for each adaptive run
```
