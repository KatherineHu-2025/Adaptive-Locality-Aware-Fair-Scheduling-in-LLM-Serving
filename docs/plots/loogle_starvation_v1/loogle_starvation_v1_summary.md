# Benchmark Summary: modal_grid_20260425_starvation_merged

Rows: 12
Policies: adaptive_dlpm, dlpm, fcfs, lpm

## Policy Medians
```text
               throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
policy                                                         
adaptive_dlpm                  34.787     1126.829    15471.905
dlpm                           34.818     1041.205    12772.647
fcfs                           34.794     1300.824    16203.227
lpm                            34.790      843.258    10818.428
```

## Policy Means
```text
               throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
policy                                                         
adaptive_dlpm                  34.787     1126.829    15471.905
dlpm                           34.795     1043.263    14132.809
fcfs                           34.794     1300.824    16203.227
lpm                            34.790      843.258    10818.428
```

## Best Throughput Row Per Policy
```text
       policy  rate   k  request_count  throughput_tok_per_sec  ttft_p99_ms
adaptive_dlpm   4.0 1.0             50               36.882905    3137.7814
         dlpm   4.0 1.0             50               36.904051    3118.8836
         fcfs   4.0 1.0             50               36.888857    3263.2240
          lpm   4.0 1.0             50               36.865842    2751.1426
```

## Best (Lowest) TTFT P99 Row Per Policy
```text
       policy  rate   k  request_count  throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
adaptive_dlpm   4.0 1.0             50               36.882905    1197.8389    3137.7814
         dlpm   4.0 1.0             50               36.904051    1012.0490    3118.8836
         fcfs   4.0 1.0             50               36.888857    1376.3701    3263.2240
          lpm   4.0 1.0             50               36.865842     870.8758    2751.1426
```

## Best Throughput Row Per Plot Label
```text
   plot_label        policy  rate   k  request_count  throughput_tok_per_sec  ttft_p99_ms
adaptive_dlpm adaptive_dlpm   4.0 1.0             50               36.882905    3137.7814
   dlpm_q1200          dlpm   4.0 1.0             50               36.879084    3362.4369
   dlpm_q4000          dlpm   4.0 1.0             50               36.883023    3352.6026
   dlpm_q8000          dlpm   4.0 1.0             50               36.904051    3118.8836
         fcfs          fcfs   4.0 1.0             50               36.888857    3263.2240
          lpm           lpm   4.0 1.0             50               36.865842    2751.1426
```

## Best (Lowest) TTFT P99 Row Per Plot Label
```text
   plot_label        policy  rate   k  request_count  throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
adaptive_dlpm adaptive_dlpm   4.0 1.0             50               36.882905    1197.8389    3137.7814
   dlpm_q1200          dlpm   4.0 1.0             50               36.879084    1294.3346    3362.4369
   dlpm_q4000          dlpm   4.0 1.0             50               36.883023    1070.3610    3352.6026
   dlpm_q8000          dlpm   4.0 1.0             50               36.904051    1012.0490    3118.8836
         fcfs          fcfs   4.0 1.0             50               36.888857    1376.3701    3263.2240
          lpm           lpm   4.0 1.0             50               36.865842     870.8758    2751.1426
```

## High-Load (Max Rate) Median by Policy
```text
               throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
policy                                                         
adaptive_dlpm                  34.787     1126.829    15471.905
dlpm                           34.818     1041.205    12772.647
fcfs                           34.794     1300.824    16203.227
lpm                            34.790      843.258    10818.428
```

## Median Metrics by Plot Label
```text
               throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
plot_label                                                     
lpm                            34.790      843.258    10818.428
dlpm_q4000                     34.820      945.675    12767.730
dlpm_q8000                     34.786      997.072    13762.417
adaptive_dlpm                  34.787     1126.829    15471.905
dlpm_q1200                     34.780     1187.042    15868.279
fcfs                           34.794     1300.824    16203.227
```

## Overall / Dominant / Cold Breakdown

### Overall
```text
   plot_label  throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms  count
adaptive_dlpm               32.690316    1055.8182   27806.0286    186
adaptive_dlpm               36.882905    1197.8389    3137.7814    383
          lpm               32.714141     815.6406   18885.7141    186
          lpm               36.865842     870.8758    2751.1426    383
         fcfs               32.699135    1225.2779   29143.2304    186
         fcfs               36.888857    1376.3701    3263.2240    383
   dlpm_q1200               32.681650    1079.7486   28374.1210    186
   dlpm_q1200               36.879084    1294.3346    3362.4369    383
   dlpm_q4000               32.756520     820.9887   22182.8576    186
   dlpm_q4000               36.883023    1070.3610    3352.6026    383
   dlpm_q8000               32.667284     982.0947   24405.9508    186
   dlpm_q8000               36.904051    1012.0490    3118.8836    383
```

### Dominant
```text
(no data)
```

### Cold
```text
(no data)
```

### Quick Read
```text
best_overall_by_ttft_p99: lpm (ttft_p99=2751.143 ms)
```

## Severe TTFT P99 Outliers (> 10,000 ms)
```text
   plot_label        policy  rate   k  request_count  ttft_p99_ms                                                               output_file
   dlpm_q1200          dlpm   4.0 1.0             25   28374.1210    results\modal_grid_20260425_142407\runs\dlpm_q1200_r4.0_k1.0_n25.jsonl
   dlpm_q4000          dlpm   4.0 1.0             25   22182.8576    results\modal_grid_20260425_142407\runs\dlpm_q4000_r4.0_k1.0_n25.jsonl
   dlpm_q8000          dlpm   4.0 1.0             25   24405.9508    results\modal_grid_20260425_142407\runs\dlpm_q8000_r4.0_k1.0_n25.jsonl
adaptive_dlpm adaptive_dlpm   4.0 1.0             25   27806.0286 results\modal_grid_20260425_145946\runs\adaptive_dlpm_r4.0_k1.0_n25.jsonl
         fcfs          fcfs   4.0 1.0             25   29143.2304          results\modal_grid_20260425_145946\runs\fcfs_r4.0_k1.0_n25.jsonl
          lpm           lpm   4.0 1.0             25   18885.7141           results\modal_grid_20260425_145946\runs\lpm_r4.0_k1.0_n25.jsonl
```

## Request-Level Telemetry Coverage
```text
total_request_rows: 3414
rows_with_Q_at_scheduling: 3414
rows_with_jain_control: 3414
rows_with_aimd_violated=true: 481
```

## Adaptive DLPM Median Q_at_scheduling
```text
adaptive_dlpm: 1200.00
```

## Adaptive AIMD Trace Coverage
```text
adaptive_runs_found: 2
one trace PNG is generated for each adaptive run
```
