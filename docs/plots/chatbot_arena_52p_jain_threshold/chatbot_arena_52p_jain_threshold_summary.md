# Benchmark Summary: modal_grid_20260422_011600

Rows: 24
Policies: adaptive_dlpm, dlpm, fcfs, lpm

## Policy Medians
```text
               throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
policy                                                         
adaptive_dlpm                 224.883     9265.070    15942.295
dlpm                          154.136    28535.059    40303.187
fcfs                          224.678     9571.483    15938.578
lpm                           173.489    23519.584    32714.304
```

## Policy Means
```text
               throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
policy                                                         
adaptive_dlpm                 225.056     7344.832    15577.183
dlpm                          167.550    25065.807    38850.254
fcfs                          224.719     7489.267    15640.508
lpm                           174.392    21207.709    30821.785
```

## Best Throughput Row Per Policy
```text
       policy  rate   k  request_count  throughput_tok_per_sec  ttft_p99_ms
adaptive_dlpm   1.0 1.0            100              300.014190 15903.086250
         dlpm   1.0 1.0            100              259.029768 20845.754708
         fcfs   1.0 1.0            100              299.053582 15939.428208
          lpm   1.0 1.0            100              200.370458 33957.109792
```

## Best (Lowest) TTFT P99 Row Per Policy
```text
       policy  rate   k  request_count  throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
adaptive_dlpm   0.5 1.0            100              150.442967  1220.639167 11146.602333
         dlpm   0.5 1.0            100              150.384438  3554.097250 14853.046833
         fcfs   0.5 1.0            100              150.469066  1151.214084 11258.871250
          lpm   0.5 1.0            100              150.220270  9377.892458 22078.779459
```

## High-Load (Max Rate) Median by Policy
```text
               throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
policy                                                         
adaptive_dlpm                 299.614     9477.452    15942.295
dlpm                          158.693    37126.347    50065.892
fcfs                          298.939     9624.579    15938.578
lpm                           198.511    27687.038    34868.431
```

## Severe TTFT P99 Outliers (> 10,000 ms)
```text
       policy  rate   k  request_count  ttft_p99_ms                                                                output_file
adaptive_dlpm   0.5 0.5            100 19277.539375 results/modal_grid_20260422_011600/runs/adaptive_dlpm_r0.5_k0.5_n100.jsonl
adaptive_dlpm   0.5 1.0            100 11146.602333 results/modal_grid_20260422_011600/runs/adaptive_dlpm_r0.5_k1.0_n100.jsonl
adaptive_dlpm   1.0 0.5            100 15981.503667 results/modal_grid_20260422_011600/runs/adaptive_dlpm_r1.0_k0.5_n100.jsonl
adaptive_dlpm   1.0 1.0            100 15903.086250 results/modal_grid_20260422_011600/runs/adaptive_dlpm_r1.0_k1.0_n100.jsonl
          lpm   0.5 0.5            100 31471.497417           results/modal_grid_20260422_011600/runs/lpm_r0.5_k0.5_n100.jsonl
          lpm   0.5 1.0            100 22078.779459           results/modal_grid_20260422_011600/runs/lpm_r0.5_k1.0_n100.jsonl
          lpm   1.0 0.5            100 35779.752750           results/modal_grid_20260422_011600/runs/lpm_r1.0_k0.5_n100.jsonl
          lpm   1.0 1.0            100 33957.109792           results/modal_grid_20260422_011600/runs/lpm_r1.0_k1.0_n100.jsonl
         fcfs   0.5 0.5            100 19426.002666          results/modal_grid_20260422_011600/runs/fcfs_r0.5_k0.5_n100.jsonl
         fcfs   0.5 1.0            100 11258.871250          results/modal_grid_20260422_011600/runs/fcfs_r0.5_k1.0_n100.jsonl
         fcfs   1.0 0.5            100 15937.728417          results/modal_grid_20260422_011600/runs/fcfs_r1.0_k0.5_n100.jsonl
         fcfs   1.0 1.0            100 15939.428208          results/modal_grid_20260422_011600/runs/fcfs_r1.0_k1.0_n100.jsonl
         dlpm   0.5 0.5            100 24092.258542    results/modal_grid_20260422_011600/runs/dlpm_q1200_r0.5_k0.5_n100.jsonl
         dlpm   0.5 1.0            100 14853.046833    results/modal_grid_20260422_011600/runs/dlpm_q1200_r0.5_k1.0_n100.jsonl
         dlpm   1.0 0.5            100 21244.571458    results/modal_grid_20260422_011600/runs/dlpm_q1200_r1.0_k0.5_n100.jsonl
         dlpm   1.0 1.0            100 20845.754708    results/modal_grid_20260422_011600/runs/dlpm_q1200_r1.0_k1.0_n100.jsonl
         dlpm   0.5 0.5            100 40827.175375    results/modal_grid_20260422_011600/runs/dlpm_q4000_r0.5_k0.5_n100.jsonl
         dlpm   0.5 1.0            100 29969.939875    results/modal_grid_20260422_011600/runs/dlpm_q4000_r0.5_k1.0_n100.jsonl
         dlpm   1.0 0.5            100 50100.453875    results/modal_grid_20260422_011600/runs/dlpm_q4000_r1.0_k0.5_n100.jsonl
         dlpm   1.0 1.0            100 50219.905334    results/modal_grid_20260422_011600/runs/dlpm_q4000_r1.0_k1.0_n100.jsonl
         dlpm   0.5 0.5            100 39779.197792    results/modal_grid_20260422_011600/runs/dlpm_q8000_r0.5_k0.5_n100.jsonl
         dlpm   0.5 1.0            100 73161.732875    results/modal_grid_20260422_011600/runs/dlpm_q8000_r0.5_k1.0_n100.jsonl
         dlpm   1.0 0.5            100 51077.675042    results/modal_grid_20260422_011600/runs/dlpm_q8000_r1.0_k0.5_n100.jsonl
         dlpm   1.0 1.0            100 50031.330833    results/modal_grid_20260422_011600/runs/dlpm_q8000_r1.0_k1.0_n100.jsonl
```

## Request-Level Telemetry Coverage
```text
total_request_rows: 6096
rows_with_Q_at_scheduling: 6096
rows_with_jain_control: 6096
rows_with_aimd_violated=true: 50
```

## Adaptive DLPM Median Q_at_scheduling
```text
adaptive_dlpm: 6000.00
```

## Adaptive AIMD Trace Coverage
```text
adaptive_runs_found: 4
one trace PNG is generated for each adaptive run
```
