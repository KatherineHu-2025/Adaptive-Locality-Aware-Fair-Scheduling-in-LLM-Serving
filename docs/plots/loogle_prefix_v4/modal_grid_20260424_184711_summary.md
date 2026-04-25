# Benchmark Summary: modal_grid_20260424_184711

Rows: 4
Policies: adaptive_dlpm, dlpm, fcfs, lpm

## Policy Medians
```text
               throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
policy                                                         
adaptive_dlpm                  32.935     1375.405     6527.214
dlpm                           33.890     1291.179     4711.374
fcfs                           33.078     1837.053     4369.574
lpm                            33.606     1412.976     4612.800
```

## Policy Means
```text
               throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
policy                                                         
adaptive_dlpm                  32.935     1375.405     6527.214
dlpm                           33.890     1291.179     4711.374
fcfs                           33.078     1837.053     4369.574
lpm                            33.606     1412.976     4612.800
```

## Best Throughput Row Per Policy
```text
       policy  rate   k  request_count  throughput_tok_per_sec  ttft_p99_ms
adaptive_dlpm   4.0 1.0           4000               32.935444    6527.2137
         dlpm   4.0 1.0           4000               33.889739    4711.3738
         fcfs   4.0 1.0           4000               33.078260    4369.5740
          lpm   4.0 1.0           4000               33.606097    4612.8000
```

## Best (Lowest) TTFT P99 Row Per Policy
```text
       policy  rate   k  request_count  throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
adaptive_dlpm   4.0 1.0           4000               32.935444    1375.4055    6527.2137
         dlpm   4.0 1.0           4000               33.889739    1291.1794    4711.3738
         fcfs   4.0 1.0           4000               33.078260    1837.0528    4369.5740
          lpm   4.0 1.0           4000               33.606097    1412.9765    4612.8000
```

## Best Throughput Row Per Plot Label
```text
   plot_label        policy  rate   k  request_count  throughput_tok_per_sec  ttft_p99_ms
adaptive_dlpm adaptive_dlpm   4.0 1.0           4000               32.935444    6527.2137
   dlpm_q4000          dlpm   4.0 1.0           4000               33.889739    4711.3738
         fcfs          fcfs   4.0 1.0           4000               33.078260    4369.5740
          lpm           lpm   4.0 1.0           4000               33.606097    4612.8000
```

## Best (Lowest) TTFT P99 Row Per Plot Label
```text
   plot_label        policy  rate   k  request_count  throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
adaptive_dlpm adaptive_dlpm   4.0 1.0           4000               32.935444    1375.4055    6527.2137
   dlpm_q4000          dlpm   4.0 1.0           4000               33.889739    1291.1794    4711.3738
         fcfs          fcfs   4.0 1.0           4000               33.078260    1837.0528    4369.5740
          lpm           lpm   4.0 1.0           4000               33.606097    1412.9765    4612.8000
```

## High-Load (Max Rate) Median by Policy
```text
               throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
policy                                                         
adaptive_dlpm                  32.935     1375.405     6527.214
dlpm                           33.890     1291.179     4711.374
fcfs                           33.078     1837.053     4369.574
lpm                            33.606     1412.976     4612.800
```

## Median Metrics by Plot Label
```text
               throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
plot_label                                                     
fcfs                           33.078     1837.053     4369.574
lpm                            33.606     1412.976     4612.800
dlpm_q4000                     33.890     1291.179     4711.374
adaptive_dlpm                  32.935     1375.405     6527.214
```

## Overall / Dominant / Cold Breakdown

### Overall
```text
   plot_label  throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms  count
adaptive_dlpm               32.935444    1375.4055    6527.2137   3971
          lpm               33.606097    1412.9765    4612.8000   3999
         fcfs               33.078260    1837.0528    4369.5740   4000
   dlpm_q4000               33.889739    1291.1794    4711.3738   4000
```

### Dominant
```text
   plot_label  throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms  count
adaptive_dlpm               10.296739    1146.1506    6900.2878   1986
          lpm               10.533040    1199.0785    3348.7452   2000
         fcfs               10.363195    1512.2958    4188.4909   2000
   dlpm_q4000               10.619105    1064.0305    1928.0973   2000
```

### Cold
```text
   plot_label  throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms  count
adaptive_dlpm               22.638704    2127.0136    6110.2911   1985
          lpm               23.073056    1983.3289    4749.7422   1999
         fcfs               22.715065    2063.8310    4445.7449   2000
   dlpm_q4000               23.270634    2211.2681    4956.9090   2000
```

### Quick Read
```text
best_overall_by_ttft_p99: fcfs (ttft_p99=4369.574 ms)
best_dominant_by_ttft_p99: dlpm_q4000 (ttft_p99=1928.097 ms)
worst_cold_by_ttft_p99: adaptive_dlpm (ttft_p99=6110.291 ms)
```

## Request-Level Telemetry Coverage
```text
total_request_rows: 16000
rows_with_Q_at_scheduling: 15970
rows_with_jain_control: 15970
rows_with_aimd_violated=true: 211
```

## Adaptive DLPM Median Q_at_scheduling
```text
adaptive_dlpm: 16000.00
```

## Adaptive AIMD Trace Coverage
```text
adaptive_runs_found: 1
one trace PNG is generated for each adaptive run
```
