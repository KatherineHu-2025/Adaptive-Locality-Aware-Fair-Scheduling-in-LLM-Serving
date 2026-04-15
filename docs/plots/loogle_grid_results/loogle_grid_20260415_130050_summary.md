# Benchmark Summary: modal_grid_20260415_130050

Rows: 18
Policies: adaptive_dlpm, fcfs, lpm

## Policy Medians
```text
               throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
policy                                                         
adaptive_dlpm                   0.665     2857.901   599852.846
fcfs                            0.657     2337.134   352746.313
lpm                             0.651     4107.824   303682.903
```

## Policy Means
```text
               throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
policy                                                         
adaptive_dlpm                   0.668     2729.176   401705.854
fcfs                            0.648     2511.749   318221.013
lpm                             0.655     4174.763   303817.514
```

## Best Throughput Row Per Policy
```text
       policy  rate   k  request_count  throughput_tok_per_sec  ttft_p99_ms
adaptive_dlpm   3.0 0.5             30                0.691450  600688.2512
         fcfs   3.0 0.5             30                0.690200  596173.9266
          lpm   2.0 0.5             30                0.680293  600909.1102
```

## Best (Lowest) TTFT P99 Row Per Policy
```text
       policy  rate   k  request_count  throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
adaptive_dlpm   2.0 1.0             30                0.648562    2844.9513    4557.6924
         fcfs   3.0 1.0             30                0.652724    2383.6782    3957.0767
          lpm   3.0 1.0             30                0.640444    4106.0250    7270.7608
```

## High-Load (Max Rate) Median by Policy
```text
               throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
policy                                                         
adaptive_dlpm                   0.670     2935.550   302710.697
fcfs                            0.671     2301.667   300065.502
lpm                             0.657     4107.824   303651.489
```

## Severe TTFT P99 Outliers (> 10,000 ms)
```text
       policy  rate   k  request_count  ttft_p99_ms                                                               output_file
         fcfs   1.0 0.5             30  599661.1799          results\modal_grid_20260415_130050\runs\fcfs_r1.0_k0.5_n30.jsonl
         fcfs   1.0 1.0             30  111854.5849          results\modal_grid_20260415_130050\runs\fcfs_r1.0_k1.0_n30.jsonl
         fcfs   2.0 0.5             30  593638.0409          results\modal_grid_20260415_130050\runs\fcfs_r2.0_k0.5_n30.jsonl
         fcfs   3.0 0.5             30  596173.9266          results\modal_grid_20260415_130050\runs\fcfs_r3.0_k0.5_n30.jsonl
          lpm   1.0 0.5             30  600061.3878           results\modal_grid_20260415_130050\runs\lpm_r1.0_k0.5_n30.jsonl
          lpm   2.0 0.5             30  600909.1102           results\modal_grid_20260415_130050\runs\lpm_r2.0_k0.5_n30.jsonl
          lpm   3.0 0.5             30  600032.2176           results\modal_grid_20260415_130050\runs\lpm_r3.0_k0.5_n30.jsonl
adaptive_dlpm   1.0 0.5             30  599358.4227 results\modal_grid_20260415_130050\runs\adaptive_dlpm_r1.0_k0.5_n30.jsonl
adaptive_dlpm   1.0 1.0             30  600550.3465 results\modal_grid_20260415_130050\runs\adaptive_dlpm_r1.0_k1.0_n30.jsonl
adaptive_dlpm   2.0 0.5             30  600347.2699 results\modal_grid_20260415_130050\runs\adaptive_dlpm_r2.0_k0.5_n30.jsonl
adaptive_dlpm   3.0 0.5             30  600688.2512 results\modal_grid_20260415_130050\runs\adaptive_dlpm_r3.0_k0.5_n30.jsonl
```
