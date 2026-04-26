# Benchmark Summary: modal_grid_20260425_163753

Rows: 12
Policies: adaptive_dlpm, dlpm, fcfs, lpm

## Policy Medians
```text
               throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
policy                                                         
adaptive_dlpm                   8.693      484.873    14419.088
dlpm                            8.695      513.636    13384.613
fcfs                            8.693      338.744     9505.827
lpm                             8.694      362.187    10242.310
```

## Policy Means
```text
               throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
policy                                                         
adaptive_dlpm                   8.693      484.873    14419.088
dlpm                            8.695      513.490    14595.847
fcfs                            8.693      338.744     9505.827
lpm                             8.694      362.187    10242.310
```

## Best Throughput Row Per Policy
```text
       policy  rate   k  request_count  throughput_tok_per_sec  ttft_p99_ms
adaptive_dlpm   1.0 1.0             50                9.218403    1084.8521
         dlpm   1.0 1.0             50                9.222576    1308.2605
         fcfs   1.0 1.0             50                9.218466     998.3459
          lpm   1.0 1.0             50                9.216968    1039.9748
```

## Best (Lowest) TTFT P99 Row Per Policy
```text
       policy  rate   k  request_count  throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
adaptive_dlpm   1.0 1.0             50                9.218403     525.0707    1084.8521
         dlpm   1.0 1.0             50                9.216836     585.7526    1230.9541
         fcfs   1.0 1.0             50                9.218466     432.0495     998.3459
          lpm   1.0 1.0             50                9.216968     444.8493    1039.9748
```

## Best Throughput Row Per Plot Label
```text
   plot_label        policy  rate   k  request_count  throughput_tok_per_sec  ttft_p99_ms
adaptive_dlpm adaptive_dlpm   1.0 1.0             50                9.218403    1084.8521
   dlpm_q1200          dlpm   1.0 1.0             50                9.222576    1308.2605
   dlpm_q4000          dlpm   1.0 1.0             50                9.216836    1230.9541
   dlpm_q8000          dlpm   1.0 1.0             50                9.219826    1383.5708
         fcfs          fcfs   1.0 1.0             50                9.218466     998.3459
          lpm           lpm   1.0 1.0             50                9.216968    1039.9748
```

## Best (Lowest) TTFT P99 Row Per Plot Label
```text
   plot_label        policy  rate   k  request_count  throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
adaptive_dlpm adaptive_dlpm   1.0 1.0             50                9.218403     525.0707    1084.8521
   dlpm_q1200          dlpm   1.0 1.0             50                9.222576     555.9859    1308.2605
   dlpm_q4000          dlpm   1.0 1.0             50                9.216836     585.7526    1230.9541
   dlpm_q8000          dlpm   1.0 1.0             50                9.219826     620.3763    1383.5708
         fcfs          fcfs   1.0 1.0             50                9.218466     432.0495     998.3459
          lpm           lpm   1.0 1.0             50                9.216968     444.8493    1039.9748
```

## High-Load (Max Rate) Median by Policy
```text
               throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
policy                                                         
adaptive_dlpm                   8.693      484.873    14419.088
dlpm                            8.695      513.636    13384.613
fcfs                            8.693      338.744     9505.827
lpm                             8.694      362.187    10242.310
```

## Median Metrics by Plot Label
```text
               throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
plot_label                                                     
fcfs                            8.693      338.744     9505.827
lpm                             8.694      362.187    10242.310
dlpm_q4000                      8.694      528.520    13308.304
adaptive_dlpm                   8.693      484.873    14419.088
dlpm_q1200                      8.695      468.335    14616.600
dlpm_q8000                      8.697      543.614    15862.638
```

## Overall / Dominant / Cold Breakdown

### Overall
```text
   plot_label  throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms  count
adaptive_dlpm                8.167668     444.6751   27753.3231    186
adaptive_dlpm                9.218403     525.0707    1084.8521    383
          lpm                8.170579     279.5239   19444.6456    186
          lpm                9.216968     444.8493    1039.9748    383
         fcfs                8.167640     245.4384   18013.3085    186
         fcfs                9.218466     432.0495     998.3459    383
   dlpm_q1200                8.167635     380.6847   27924.9389    186
   dlpm_q1200                9.222576     555.9859    1308.2605    383
   dlpm_q4000                8.170518     471.2865   25385.6545    186
   dlpm_q4000                9.216836     585.7526    1230.9541    383
   dlpm_q8000                8.173274     466.8524   30341.7057    186
   dlpm_q8000                9.219826     620.3763    1383.5708    383
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
best_overall_by_ttft_p99: fcfs (ttft_p99=998.346 ms)
```

## Severe TTFT P99 Outliers (> 10,000 ms)
```text
   plot_label        policy  rate   k  request_count  ttft_p99_ms                                                               output_file
adaptive_dlpm adaptive_dlpm   1.0 1.0             25   27753.3231 results\modal_grid_20260425_163753\runs\adaptive_dlpm_r1.0_k1.0_n25.jsonl
         fcfs          fcfs   1.0 1.0             25   18013.3085          results\modal_grid_20260425_163753\runs\fcfs_r1.0_k1.0_n25.jsonl
          lpm           lpm   1.0 1.0             25   19444.6456           results\modal_grid_20260425_163753\runs\lpm_r1.0_k1.0_n25.jsonl
   dlpm_q1200          dlpm   1.0 1.0             25   27924.9389    results\modal_grid_20260425_163753\runs\dlpm_q1200_r1.0_k1.0_n25.jsonl
   dlpm_q4000          dlpm   1.0 1.0             25   25385.6545    results\modal_grid_20260425_163753\runs\dlpm_q4000_r1.0_k1.0_n25.jsonl
   dlpm_q8000          dlpm   1.0 1.0             25   30341.7057    results\modal_grid_20260425_163753\runs\dlpm_q8000_r1.0_k1.0_n25.jsonl
```

## Request-Level Telemetry Coverage
```text
total_request_rows: 3414
rows_with_Q_at_scheduling: 3414
rows_with_jain_control: 3414
rows_with_aimd_violated=true: 211
```

## Adaptive DLPM Median Q_at_scheduling
```text
adaptive_dlpm: 2700.00
```

## Adaptive AIMD Trace Coverage
```text
adaptive_runs_found: 2
one trace PNG is generated for each adaptive run
```
