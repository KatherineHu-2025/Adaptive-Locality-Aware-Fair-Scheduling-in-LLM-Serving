# Benchmark Summary: modal_grid_20260423_204639

Rows: 4
Policies: adaptive_dlpm, dlpm, fcfs, lpm

## Policy Medians
```text
               throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
policy                                                         
adaptive_dlpm                  31.516     1442.283    21033.838
dlpm                           31.649     1389.465    26797.722
fcfs                           31.120     1795.760    20661.666
lpm                            31.270     1438.892    25299.127
```

## Policy Means
```text
               throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
policy                                                         
adaptive_dlpm                  31.516     1442.283    21033.838
dlpm                           31.649     1389.465    26797.722
fcfs                           31.120     1795.760    20661.666
lpm                            31.270     1438.892    25299.127
```

## Best Throughput Row Per Policy
```text
       policy  rate   k  request_count  throughput_tok_per_sec  ttft_p99_ms
adaptive_dlpm   4.0 1.0            600               31.516001   21033.8383
         dlpm   4.0 1.0            600               31.649419   26797.7217
         fcfs   4.0 1.0            600               31.119690   20661.6664
          lpm   4.0 1.0            600               31.269584   25299.1271
```

## Best (Lowest) TTFT P99 Row Per Policy
```text
       policy  rate   k  request_count  throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
adaptive_dlpm   4.0 1.0            600               31.516001    1442.2834   21033.8383
         dlpm   4.0 1.0            600               31.649419    1389.4645   26797.7217
         fcfs   4.0 1.0            600               31.119690    1795.7603   20661.6664
          lpm   4.0 1.0            600               31.269584    1438.8923   25299.1271
```

## Best Throughput Row Per Plot Label
```text
   plot_label        policy  rate   k  request_count  throughput_tok_per_sec  ttft_p99_ms
adaptive_dlpm adaptive_dlpm   4.0 1.0            600               31.516001   21033.8383
   dlpm_q4000          dlpm   4.0 1.0            600               31.649419   26797.7217
         fcfs          fcfs   4.0 1.0            600               31.119690   20661.6664
          lpm           lpm   4.0 1.0            600               31.269584   25299.1271
```

## Best (Lowest) TTFT P99 Row Per Plot Label
```text
   plot_label        policy  rate   k  request_count  throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
adaptive_dlpm adaptive_dlpm   4.0 1.0            600               31.516001    1442.2834   21033.8383
   dlpm_q4000          dlpm   4.0 1.0            600               31.649419    1389.4645   26797.7217
         fcfs          fcfs   4.0 1.0            600               31.119690    1795.7603   20661.6664
          lpm           lpm   4.0 1.0            600               31.269584    1438.8923   25299.1271
```

## High-Load (Max Rate) Median by Policy
```text
               throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
policy                                                         
adaptive_dlpm                  31.516     1442.283    21033.838
dlpm                           31.649     1389.465    26797.722
fcfs                           31.120     1795.760    20661.666
lpm                            31.270     1438.892    25299.127
```

## Median Metrics by Plot Label
```text
               throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
plot_label                                                     
fcfs                           31.120     1795.760    20661.666
adaptive_dlpm                  31.516     1442.283    21033.838
lpm                            31.270     1438.892    25299.127
dlpm_q4000                     31.649     1389.465    26797.722
```

## Overall / Dominant / Cold Breakdown

### Overall
```text
   plot_label  throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms  count
adaptive_dlpm               31.516001    1442.2834   21033.8383    600
          lpm               31.269584    1438.8923   25299.1271    600
         fcfs               31.119690    1795.7603   20661.6664    600
   dlpm_q4000               31.649419    1389.4645   26797.7217    600
```

### Dominant
```text
   plot_label  throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms  count
adaptive_dlpm                9.691080    1260.7801   22170.8615    300
          lpm                9.610122    1327.1765   26910.2853    300
         fcfs                9.555849    1540.1410   21838.5086    300
   dlpm_q4000                9.713582    1179.1426   27931.0483    300
```

### Cold
```text
   plot_label  throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms  count
adaptive_dlpm               21.824921    2279.7815    5258.9116    300
          lpm               21.659462    1988.6589    4356.6940    300
         fcfs               21.563840    2167.7610    4925.1804    300
   dlpm_q4000               21.935837    2103.8177    5365.2840    300
```

### Quick Read
```text
best_overall_by_ttft_p99: fcfs (ttft_p99=20661.666 ms)
best_dominant_by_ttft_p99: fcfs (ttft_p99=21838.509 ms)
worst_cold_by_ttft_p99: dlpm_q4000 (ttft_p99=5365.284 ms)
```

## Severe TTFT P99 Outliers (> 10,000 ms)
```text
   plot_label        policy  rate   k  request_count  ttft_p99_ms                                                                output_file
adaptive_dlpm adaptive_dlpm   4.0 1.0            600   21033.8383 results\modal_grid_20260423_204639\runs\adaptive_dlpm_r4.0_k1.0_n600.jsonl
          lpm           lpm   4.0 1.0            600   25299.1271           results\modal_grid_20260423_204639\runs\lpm_r4.0_k1.0_n600.jsonl
         fcfs          fcfs   4.0 1.0            600   20661.6664          results\modal_grid_20260423_204639\runs\fcfs_r4.0_k1.0_n600.jsonl
   dlpm_q4000          dlpm   4.0 1.0            600   26797.7217    results\modal_grid_20260423_204639\runs\dlpm_q4000_r4.0_k1.0_n600.jsonl
```

## Request-Level Telemetry Coverage
```text
total_request_rows: 2400
rows_with_Q_at_scheduling: 2400
rows_with_jain_control: 2400
rows_with_aimd_violated=true: 76
```

## Adaptive DLPM Median Q_at_scheduling
```text
adaptive_dlpm: 4750.00
```

## Adaptive AIMD Trace Coverage
```text
adaptive_runs_found: 1
one trace PNG is generated for each adaptive run
```
