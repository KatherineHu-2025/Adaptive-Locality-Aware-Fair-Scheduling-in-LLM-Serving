# Benchmark Summary: modal_grid_20260414_234633

Rows: 18
Policies: adaptive_dlpm, fcfs, lpm

## Policy Medians
```text
               throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
policy                                                         
adaptive_dlpm                  44.097     2411.437     4103.434
fcfs                           44.101     1106.332     3026.286
lpm                            44.096     2380.977     4025.131
```

## Policy Means
```text
               throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
policy                                                         
adaptive_dlpm                  43.650     2354.620    28007.174
fcfs                           42.733     1235.097    52969.679
lpm                            44.097     2204.577     7430.892
```

## Best Throughput Row Per Policy
```text
       policy  rate   k  request_count  throughput_tok_per_sec  ttft_p99_ms
adaptive_dlpm   3.0 0.5             30               66.573437    4066.7247
         fcfs   3.0 0.5             30               66.573372    2842.2919
          lpm   3.0 0.5             30               66.579216    3997.2429
```

## Best (Lowest) TTFT P99 Row Per Policy
```text
       policy  rate   k  request_count  throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
adaptive_dlpm   2.0 0.5             30               44.385012    2517.1035    4037.1173
         fcfs   2.0 0.5             30               44.389083     228.2671    2738.2236
          lpm   2.0 0.5             30               44.382685    2177.2333    3968.0745
```

## High-Load (Max Rate) Median by Policy
```text
               throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
policy                                                         
adaptive_dlpm                  66.145     2416.360     4068.794
fcfs                           66.142     1342.765     3015.719
lpm                            66.143     2502.534     4602.782
```

## Severe TTFT P99 Outliers (> 10,000 ms)
```text
       policy  rate   k  request_count  ttft_p99_ms                                                               output_file
         fcfs   1.0 0.5             30  146723.9710          results\modal_grid_20260414_234633\runs\fcfs_r1.0_k0.5_n30.jsonl
         fcfs   1.0 1.0             30  159461.0151          results\modal_grid_20260414_234633\runs\fcfs_r1.0_k1.0_n30.jsonl
          lpm   1.0 0.5             30   23361.4509           results\modal_grid_20260414_234633\runs\lpm_r1.0_k0.5_n30.jsonl
adaptive_dlpm   1.0 0.5             30  147506.2704 results\modal_grid_20260414_234633\runs\adaptive_dlpm_r1.0_k0.5_n30.jsonl
```
