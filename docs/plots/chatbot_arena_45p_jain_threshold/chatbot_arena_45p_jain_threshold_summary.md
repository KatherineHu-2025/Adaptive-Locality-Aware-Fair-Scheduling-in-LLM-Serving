# Benchmark Summary: modal_grid_20260421_230336

Rows: 24
Policies: adaptive_dlpm, dlpm, fcfs, lpm

## Policy Medians
```text
               throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
policy                                                         
adaptive_dlpm                 205.317    13941.320    20980.047
dlpm                          197.339    14224.349    21761.617
fcfs                          225.199     6424.616    13951.489
lpm                           225.317     5964.971    13600.783
```

## Policy Means
```text
               throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
policy                                                         
adaptive_dlpm                 205.486    11330.568    20225.022
dlpm                          201.033    14332.595    44164.563
fcfs                          225.305     5084.223    12999.450
lpm                           207.409    12509.716    80330.536
```

## Best Throughput Row Per Policy
```text
       policy  rate   k  request_count  throughput_tok_per_sec  ttft_p99_ms
adaptive_dlpm   1.0 1.0            100              260.917383 20993.686542
         dlpm   1.0 1.0            100              299.923386 14340.697375
         fcfs   1.0 0.5            100              300.259772 13927.098542
          lpm   1.0 0.5            100              300.194732 13891.734875
```

## Best (Lowest) TTFT P99 Row Per Policy
```text
       policy  rate   k  request_count  throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
adaptive_dlpm   0.5 1.0            100              150.411733  3167.100458 14961.034292
         dlpm   0.5 1.0            100              150.493523   890.666708  9662.567292
         fcfs   0.5 1.0            100              150.575342   760.164375  9255.523042
          lpm   0.5 1.0            100              150.548941   704.271709  9457.415042
```

## High-Load (Max Rate) Median by Policy
```text
               throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
policy                                                         
adaptive_dlpm                 260.569    14183.715    20980.047
dlpm                          254.965    15699.411    21761.617
fcfs                          300.041     6670.966    13951.489
lpm                           300.139     5964.971    13600.783
```

## Severe TTFT P99 Outliers (> 10,000 ms)
```text
       policy  rate   k  request_count   ttft_p99_ms                                                                output_file
adaptive_dlpm   0.5 0.5            100  23978.960459 results/modal_grid_20260421_230336/runs/adaptive_dlpm_r0.5_k0.5_n100.jsonl
adaptive_dlpm   0.5 1.0            100  14961.034292 results/modal_grid_20260421_230336/runs/adaptive_dlpm_r0.5_k1.0_n100.jsonl
adaptive_dlpm   1.0 0.5            100  20966.407541 results/modal_grid_20260421_230336/runs/adaptive_dlpm_r1.0_k0.5_n100.jsonl
adaptive_dlpm   1.0 1.0            100  20993.686542 results/modal_grid_20260421_230336/runs/adaptive_dlpm_r1.0_k1.0_n100.jsonl
          lpm   0.5 0.5            100 284663.162000           results/modal_grid_20260421_230336/runs/lpm_r0.5_k0.5_n100.jsonl
          lpm   1.0 0.5            100  13891.734875           results/modal_grid_20260421_230336/runs/lpm_r1.0_k0.5_n100.jsonl
          lpm   1.0 1.0            100  13309.831417           results/modal_grid_20260421_230336/runs/lpm_r1.0_k1.0_n100.jsonl
         fcfs   0.5 0.5            100  14839.296917          results/modal_grid_20260421_230336/runs/fcfs_r0.5_k0.5_n100.jsonl
         fcfs   1.0 0.5            100  13927.098542          results/modal_grid_20260421_230336/runs/fcfs_r1.0_k0.5_n100.jsonl
         fcfs   1.0 1.0            100  13975.879750          results/modal_grid_20260421_230336/runs/fcfs_r1.0_k1.0_n100.jsonl
         dlpm   0.5 0.5            100  18729.944875    results/modal_grid_20260421_230336/runs/dlpm_q1200_r0.5_k0.5_n100.jsonl
         dlpm   0.5 1.0            100 174633.544417    results/modal_grid_20260421_230336/runs/dlpm_q1200_r0.5_k1.0_n100.jsonl
         dlpm   1.0 0.5            100  25109.969542    results/modal_grid_20260421_230336/runs/dlpm_q1200_r1.0_k0.5_n100.jsonl
         dlpm   1.0 1.0            100  21242.449875    results/modal_grid_20260421_230336/runs/dlpm_q1200_r1.0_k1.0_n100.jsonl
         dlpm   0.5 0.5            100 166577.929750    results/modal_grid_20260421_230336/runs/dlpm_q4000_r0.5_k0.5_n100.jsonl
         dlpm   1.0 0.5            100  14098.681000    results/modal_grid_20260421_230336/runs/dlpm_q4000_r1.0_k0.5_n100.jsonl
         dlpm   1.0 1.0            100  14340.697375    results/modal_grid_20260421_230336/runs/dlpm_q4000_r1.0_k1.0_n100.jsonl
         dlpm   0.5 0.5            100  24385.314125    results/modal_grid_20260421_230336/runs/dlpm_q8000_r0.5_k0.5_n100.jsonl
         dlpm   0.5 1.0            100  15466.534666    results/modal_grid_20260421_230336/runs/dlpm_q8000_r0.5_k1.0_n100.jsonl
         dlpm   1.0 0.5            100  23446.336000    results/modal_grid_20260421_230336/runs/dlpm_q8000_r1.0_k0.5_n100.jsonl
         dlpm   1.0 1.0            100  22280.784834    results/modal_grid_20260421_230336/runs/dlpm_q8000_r1.0_k1.0_n100.jsonl
```

## Request-Level Telemetry Coverage
```text
total_request_rows: 6096
rows_with_Q_at_scheduling: 6096
rows_with_jain_control: 6096
rows_with_aimd_violated=true: 0
```

## Adaptive DLPM Median Q_at_scheduling
```text
adaptive_dlpm: 9000.00
```

## Adaptive AIMD Trace Coverage
```text
adaptive_runs_found: 4
one trace PNG is generated for each adaptive run
```
