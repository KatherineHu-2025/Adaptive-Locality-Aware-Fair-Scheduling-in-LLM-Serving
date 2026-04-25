# Benchmark Summary: modal_grid_20260424_212104

Rows: 4
Policies: adaptive_dlpm, dlpm, fcfs, lpm

## Policy Medians
```text
               throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
policy                                                         
adaptive_dlpm                  34.433     1043.319     4907.639
dlpm                           32.186     1555.092     5265.667
fcfs                           27.914     2129.436     4630.038
lpm                            31.444     1508.407     4587.457
```

## Policy Means
```text
               throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
policy                                                         
adaptive_dlpm                  34.433     1043.319     4907.639
dlpm                           32.186     1555.092     5265.667
fcfs                           27.914     2129.436     4630.038
lpm                            31.444     1508.407     4587.457
```

## Best Throughput Row Per Policy
```text
       policy  rate   k  request_count  throughput_tok_per_sec  ttft_p99_ms
adaptive_dlpm   4.0 1.0           1500               34.433495    4907.6388
         dlpm   4.0 1.0           1500               32.186195    5265.6672
         fcfs   4.0 1.0           1500               27.914433    4630.0385
          lpm   4.0 1.0           1500               31.444064    4587.4574
```

## Best (Lowest) TTFT P99 Row Per Policy
```text
       policy  rate   k  request_count  throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
adaptive_dlpm   4.0 1.0           1500               34.433495    1043.3187    4907.6388
         dlpm   4.0 1.0           1500               32.186195    1555.0919    5265.6672
         fcfs   4.0 1.0           1500               27.914433    2129.4362    4630.0385
          lpm   4.0 1.0           1500               31.444064    1508.4072    4587.4574
```

## Best Throughput Row Per Plot Label
```text
   plot_label        policy  rate   k  request_count  throughput_tok_per_sec  ttft_p99_ms
adaptive_dlpm adaptive_dlpm   4.0 1.0           1500               34.433495    4907.6388
   dlpm_q4000          dlpm   4.0 1.0           1500               32.186195    5265.6672
         fcfs          fcfs   4.0 1.0           1500               27.914433    4630.0385
          lpm           lpm   4.0 1.0           1500               31.444064    4587.4574
```

## Best (Lowest) TTFT P99 Row Per Plot Label
```text
   plot_label        policy  rate   k  request_count  throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
adaptive_dlpm adaptive_dlpm   4.0 1.0           1500               34.433495    1043.3187    4907.6388
   dlpm_q4000          dlpm   4.0 1.0           1500               32.186195    1555.0919    5265.6672
         fcfs          fcfs   4.0 1.0           1500               27.914433    2129.4362    4630.0385
          lpm           lpm   4.0 1.0           1500               31.444064    1508.4072    4587.4574
```

## High-Load (Max Rate) Median by Policy
```text
               throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
policy                                                         
adaptive_dlpm                  34.433     1043.319     4907.639
dlpm                           32.186     1555.092     5265.667
fcfs                           27.914     2129.436     4630.038
lpm                            31.444     1508.407     4587.457
```

## Median Metrics by Plot Label
```text
               throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
plot_label                                                     
lpm                            31.444     1508.407     4587.457
fcfs                           27.914     2129.436     4630.038
adaptive_dlpm                  34.433     1043.319     4907.639
dlpm_q4000                     32.186     1555.092     5265.667
```

## Overall / Dominant / Cold Breakdown

### Overall
```text
   plot_label  throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms  count
adaptive_dlpm               34.433495    1043.3187    4907.6388   1500
          lpm               31.444064    1508.4072    4587.4574   1500
         fcfs               27.914433    2129.4362    4630.0385   1500
   dlpm_q4000               32.186195    1555.0919    5265.6672   1500
```

### Dominant
```text
   plot_label  throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms  count
adaptive_dlpm               10.807242     753.8010    2071.0801    750
          lpm                9.858421    1411.6525    2168.6813    750
         fcfs                8.746754    1959.0836    4575.0195    750
   dlpm_q4000               10.092140    1356.6675    3501.5729    750
```

### Cold
```text
   plot_label  throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms  count
adaptive_dlpm               23.626253    2044.4953    5437.0964    750
          lpm               21.585643    2121.8133    4993.5450    750
         fcfs               19.167679    2357.3675    4708.6930    750
   dlpm_q4000               22.094055    2303.9620    5410.7547    750
```

### Quick Read
```text
best_overall_by_ttft_p99: lpm (ttft_p99=4587.457 ms)
best_dominant_by_ttft_p99: adaptive_dlpm (ttft_p99=2071.080 ms)
worst_cold_by_ttft_p99: adaptive_dlpm (ttft_p99=5437.096 ms)
```

## Request-Level Telemetry Coverage
```text
total_request_rows: 6000
rows_with_Q_at_scheduling: 6000
rows_with_jain_control: 6000
rows_with_aimd_violated=true: 763
```

## Adaptive DLPM Median Q_at_scheduling
```text
adaptive_dlpm: 1700.00
```

## Adaptive AIMD Trace Coverage
```text
adaptive_runs_found: 1
one trace PNG is generated for each adaptive run
```
