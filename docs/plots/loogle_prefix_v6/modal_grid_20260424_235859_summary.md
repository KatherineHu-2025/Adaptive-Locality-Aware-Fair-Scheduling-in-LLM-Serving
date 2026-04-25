# Benchmark Summary: modal_grid_20260424_235859

Rows: 4
Policies: adaptive_dlpm, dlpm, fcfs, lpm

## Policy Medians
```text
               throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
policy                                                         
adaptive_dlpm                  34.670     1158.682     4714.167
dlpm                           34.282     1171.822     4654.554
fcfs                           31.410     1911.180     4518.194
lpm                            31.640     1488.621     4535.418
```

## Policy Means
```text
               throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
policy                                                         
adaptive_dlpm                  34.670     1158.682     4714.167
dlpm                           34.282     1171.822     4654.554
fcfs                           31.410     1911.180     4518.194
lpm                            31.640     1488.621     4535.418
```

## Best Throughput Row Per Policy
```text
       policy  rate   k  request_count  throughput_tok_per_sec  ttft_p99_ms
adaptive_dlpm   4.0 1.0           1500               34.669842    4714.1673
         dlpm   4.0 1.0           1500               34.281535    4654.5540
         fcfs   4.0 1.0           1500               31.410020    4518.1938
          lpm   4.0 1.0           1500               31.640206    4535.4183
```

## Best (Lowest) TTFT P99 Row Per Policy
```text
       policy  rate   k  request_count  throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
adaptive_dlpm   4.0 1.0           1500               34.669842    1158.6818    4714.1673
         dlpm   4.0 1.0           1500               34.281535    1171.8216    4654.5540
         fcfs   4.0 1.0           1500               31.410020    1911.1795    4518.1938
          lpm   4.0 1.0           1500               31.640206    1488.6206    4535.4183
```

## Best Throughput Row Per Plot Label
```text
   plot_label        policy  rate   k  request_count  throughput_tok_per_sec  ttft_p99_ms
adaptive_dlpm adaptive_dlpm   4.0 1.0           1500               34.669842    4714.1673
   dlpm_q4000          dlpm   4.0 1.0           1500               34.281535    4654.5540
         fcfs          fcfs   4.0 1.0           1500               31.410020    4518.1938
          lpm           lpm   4.0 1.0           1500               31.640206    4535.4183
```

## Best (Lowest) TTFT P99 Row Per Plot Label
```text
   plot_label        policy  rate   k  request_count  throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
adaptive_dlpm adaptive_dlpm   4.0 1.0           1500               34.669842    1158.6818    4714.1673
   dlpm_q4000          dlpm   4.0 1.0           1500               34.281535    1171.8216    4654.5540
         fcfs          fcfs   4.0 1.0           1500               31.410020    1911.1795    4518.1938
          lpm           lpm   4.0 1.0           1500               31.640206    1488.6206    4535.4183
```

## High-Load (Max Rate) Median by Policy
```text
               throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
policy                                                         
adaptive_dlpm                  34.670     1158.682     4714.167
dlpm                           34.282     1171.822     4654.554
fcfs                           31.410     1911.180     4518.194
lpm                            31.640     1488.621     4535.418
```

## Median Metrics by Plot Label
```text
               throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
plot_label                                                     
fcfs                           31.410     1911.180     4518.194
lpm                            31.640     1488.621     4535.418
dlpm_q4000                     34.282     1171.822     4654.554
adaptive_dlpm                  34.670     1158.682     4714.167
```

## Overall / Dominant / Cold Breakdown

### Overall
```text
   plot_label  throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms  count
adaptive_dlpm               34.669842    1158.6818    4714.1673   1500
          lpm               31.640206    1488.6206    4535.4183   1500
         fcfs               31.410020    1911.1795    4518.1938   1500
   dlpm_q4000               34.281535    1171.8216    4654.5540   1500
```

### Dominant
```text
   plot_label  throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms  count
adaptive_dlpm               10.870337     947.0102    2574.8662    750
          lpm                9.920846    1323.5614    2151.0374    750
         fcfs                9.850393    1685.5525    4206.2224    750
   dlpm_q4000               10.748483     865.5252    2440.7786    750
```

### Cold
```text
   plot_label  throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms  count
adaptive_dlpm               23.799505    2071.2812    4884.0518    750
          lpm               21.719361    2169.8016    4733.5452    750
         fcfs               21.559627    2136.1999    4603.8114    750
   dlpm_q4000               23.533053    2114.7841    5260.5864    750
```

### Quick Read
```text
best_overall_by_ttft_p99: fcfs (ttft_p99=4518.194 ms)
best_dominant_by_ttft_p99: lpm (ttft_p99=2151.037 ms)
worst_cold_by_ttft_p99: dlpm_q4000 (ttft_p99=5260.586 ms)
```

## Request-Level Telemetry Coverage
```text
total_request_rows: 6000
rows_with_Q_at_scheduling: 6000
rows_with_jain_control: 6000
rows_with_aimd_violated=true: 1142
```

## Adaptive DLPM Median Q_at_scheduling
```text
adaptive_dlpm: 2200.00
```

## Adaptive AIMD Trace Coverage
```text
adaptive_runs_found: 1
one trace PNG is generated for each adaptive run
```
