# Benchmark Summary: modal_grid_20260421_161221

Rows: 2
Policies: adaptive_dlpm

## Policy Medians
```text
               throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
policy                                                         
adaptive_dlpm                   8.692      808.134    89111.501
```

## Policy Means
```text
               throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
policy                                                         
adaptive_dlpm                   8.692      808.134    89111.501
```

## Best Throughput Row Per Policy
```text
       policy  rate   k  request_count  throughput_tok_per_sec  ttft_p99_ms
adaptive_dlpm   1.0 1.0             50                9.216939    2566.0765
```

## Best (Lowest) TTFT P99 Row Per Policy
```text
       policy  rate   k  request_count  throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
adaptive_dlpm   1.0 1.0             50                9.216939    1001.7839    2566.0765
```

## High-Load (Max Rate) Median by Policy
```text
               throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
policy                                                         
adaptive_dlpm                   8.692      808.134    89111.501
```

## Severe TTFT P99 Outliers (> 10,000 ms)
```text
       policy  rate   k  request_count  ttft_p99_ms                                                               output_file
adaptive_dlpm   1.0 1.0             25  175656.9264 results\modal_grid_20260421_161221\runs\adaptive_dlpm_r1.0_k1.0_n25.jsonl
```

## Request-Level Telemetry Coverage
```text
total_request_rows: 569
rows_with_Q_at_scheduling: 569
rows_with_jain_control: 569
rows_with_aimd_violated=true: 107
```

## Adaptive DLPM Median Q_at_scheduling
```text
adaptive_dlpm: 4500.00
```

## Adaptive AIMD Trace Coverage
```text
adaptive_runs_found: 2
one trace PNG is generated for each adaptive run
```
