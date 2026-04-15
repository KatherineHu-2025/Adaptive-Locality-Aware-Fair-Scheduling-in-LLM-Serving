# Benchmark Summary: modal_grid_20260414_200819

Rows: 60
Policies: fcfs, lpm

## Policy Medians
```text
        throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
policy                                                  
fcfs                    77.660      151.355      781.176
lpm                     77.649     1108.589     2758.572
```

## Policy Means
```text
        throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
policy                                                  
fcfs                    82.145      195.394     10931.84
lpm                     75.025     1345.661      6689.17
```

## Best Throughput Row Per Policy
```text
policy  rate   k  request_count  throughput_tok_per_sec  ttft_p99_ms
  fcfs   3.0 1.0             50              169.508178     854.2071
   lpm   3.0 0.5             50              119.750733    2860.0895
```

## Best (Lowest) TTFT P99 Row Per Policy
```text
policy  rate   k  request_count  throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
  fcfs   0.5 1.0             50               28.252610     145.3013     258.4116
   lpm   0.5 1.0             50               28.251778     467.4396    1065.6730
```

## High-Load (Max Rate) Median by Policy
```text
        throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
policy                                                  
fcfs                   155.314      196.882     1063.723
lpm                    117.795     2465.051     2864.677
```

## Severe TTFT P99 Outliers (> 10,000 ms)
```text
policy  rate   k  request_count  ttft_p99_ms                                                      output_file
  fcfs   0.5 0.5             50  306347.1253 results\modal_grid_20260414_200819\runs\fcfs_r0.5_k0.5_n50.jsonl
   lpm   0.5 0.5             50  130232.1048  results\modal_grid_20260414_200819\runs\lpm_r0.5_k0.5_n50.jsonl
```
