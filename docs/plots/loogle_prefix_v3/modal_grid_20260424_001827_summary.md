# Benchmark Summary: modal_grid_20260424_001827

Rows: 4
Policies: adaptive_dlpm, dlpm, fcfs, lpm

## Policy Medians
```text
               throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
policy                                                         
adaptive_dlpm                  34.630     1342.664     4801.150
dlpm                           34.633     1320.990     4741.368
fcfs                           32.935     1816.520     4347.046
lpm                            33.740     1385.514     4472.292
```

## Policy Means
```text
               throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
policy                                                         
adaptive_dlpm                  34.630     1342.664     4801.150
dlpm                           34.633     1320.990     4741.368
fcfs                           32.935     1816.520     4347.046
lpm                            33.740     1385.514     4472.292
```

## Best Throughput Row Per Policy
```text
       policy  rate   k  request_count  throughput_tok_per_sec  ttft_p99_ms
adaptive_dlpm   4.0 1.0           2000               34.630402    4801.1496
         dlpm   4.0 1.0           2000               34.632862    4741.3676
         fcfs   4.0 1.0           2000               32.935340    4347.0459
          lpm   4.0 1.0           2000               33.740090    4472.2923
```

## Best (Lowest) TTFT P99 Row Per Policy
```text
       policy  rate   k  request_count  throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
adaptive_dlpm   4.0 1.0           2000               34.630402    1342.6638    4801.1496
         dlpm   4.0 1.0           2000               34.632862    1320.9899    4741.3676
         fcfs   4.0 1.0           2000               32.935340    1816.5196    4347.0459
          lpm   4.0 1.0           2000               33.740090    1385.5136    4472.2923
```

## Best Throughput Row Per Plot Label
```text
   plot_label        policy  rate   k  request_count  throughput_tok_per_sec  ttft_p99_ms
adaptive_dlpm adaptive_dlpm   4.0 1.0           2000               34.630402    4801.1496
   dlpm_q4000          dlpm   4.0 1.0           2000               34.632862    4741.3676
         fcfs          fcfs   4.0 1.0           2000               32.935340    4347.0459
          lpm           lpm   4.0 1.0           2000               33.740090    4472.2923
```

## Best (Lowest) TTFT P99 Row Per Plot Label
```text
   plot_label        policy  rate   k  request_count  throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
adaptive_dlpm adaptive_dlpm   4.0 1.0           2000               34.630402    1342.6638    4801.1496
   dlpm_q4000          dlpm   4.0 1.0           2000               34.632862    1320.9899    4741.3676
         fcfs          fcfs   4.0 1.0           2000               32.935340    1816.5196    4347.0459
          lpm           lpm   4.0 1.0           2000               33.740090    1385.5136    4472.2923
```

## High-Load (Max Rate) Median by Policy
```text
               throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
policy                                                         
adaptive_dlpm                  34.630     1342.664     4801.150
dlpm                           34.633     1320.990     4741.368
fcfs                           32.935     1816.520     4347.046
lpm                            33.740     1385.514     4472.292
```

## Median Metrics by Plot Label
```text
               throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
plot_label                                                     
fcfs                           32.935     1816.520     4347.046
lpm                            33.740     1385.514     4472.292
dlpm_q4000                     34.633     1320.990     4741.368
adaptive_dlpm                  34.630     1342.664     4801.150
```

## Overall / Dominant / Cold Breakdown

### Overall
```text
   plot_label  throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms  count
adaptive_dlpm               34.630402    1342.6638    4801.1496   2000
          lpm               33.740090    1385.5136    4472.2923   2000
         fcfs               32.935340    1816.5196    4347.0459   2000
   dlpm_q4000               34.632862    1320.9899    4741.3676   1999
```

### Dominant
```text
   plot_label  throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms  count
adaptive_dlpm               10.806441    1116.8310    2800.1384   1000
          lpm               10.527722    1152.8892    2324.8970   1000
         fcfs               10.284580    1581.5430    4098.9425   1000
   dlpm_q4000               10.803022    1111.0717    1948.5837    999
```

### Cold
```text
   plot_label  throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms  count
adaptive_dlpm               23.823961    2147.5899    5224.4356   1000
          lpm               23.212368    2015.2864    4813.9333   1000
         fcfs               22.650760    2069.1246    4562.8125   1000
   dlpm_q4000               23.829840    2144.8743    4985.7810   1000
```

### Quick Read
```text
best_overall_by_ttft_p99: fcfs (ttft_p99=4347.046 ms)
best_dominant_by_ttft_p99: dlpm_q4000 (ttft_p99=1948.584 ms)
worst_cold_by_ttft_p99: adaptive_dlpm (ttft_p99=5224.436 ms)
```

## Request-Level Telemetry Coverage
```text
total_request_rows: 8000
rows_with_Q_at_scheduling: 7999
rows_with_jain_control: 7999
rows_with_aimd_violated=true: 793
```

## Adaptive DLPM Median Q_at_scheduling
```text
adaptive_dlpm: 3550.00
```

## Adaptive AIMD Trace Coverage
```text
adaptive_runs_found: 1
one trace PNG is generated for each adaptive run
```
