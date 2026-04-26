# Benchmark Summary: modal_grid_20260426_v4_merged

Rows: 6
Policies: adaptive_dlpm, dlpm_q1200, dlpm_q4000, dlpm_q8000, fcfs, lpm

## Policy Medians
```text
               throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
policy                                                         
adaptive_dlpm                  46.151      203.819      661.805
dlpm_q1200                     46.097      237.220      682.820
dlpm_q4000                     46.085      246.474      713.347
dlpm_q8000                     46.081      252.662      700.390
fcfs                           46.078      396.350     1098.393
lpm                            46.078      295.097     1264.212
```

## Policy Means
```text
               throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
policy                                                         
adaptive_dlpm                  46.151      203.819      661.805
dlpm_q1200                     46.097      237.220      682.820
dlpm_q4000                     46.085      246.474      713.347
dlpm_q8000                     46.081      252.662      700.390
fcfs                           46.078      396.350     1098.393
lpm                            46.078      295.097     1264.212
```

## Best Throughput Row Per Policy
```text
       policy  rate   k  request_count  throughput_tok_per_sec  ttft_p99_ms
adaptive_dlpm   5.0 1.0           1800               46.151409     661.8047
   dlpm_q1200   5.0 1.0           1800               46.097400     682.8196
   dlpm_q4000   5.0 1.0           1800               46.084566     713.3465
   dlpm_q8000   5.0 1.0           1800               46.081002     700.3901
         fcfs   5.0 1.0           1800               46.078283    1098.3930
          lpm   5.0 1.0           1800               46.078436    1264.2117
```

## Best (Lowest) TTFT P99 Row Per Policy
```text
       policy  rate   k  request_count  throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
adaptive_dlpm   5.0 1.0           1800               46.151409     203.8188     661.8047
   dlpm_q1200   5.0 1.0           1800               46.097400     237.2203     682.8196
   dlpm_q4000   5.0 1.0           1800               46.084566     246.4739     713.3465
   dlpm_q8000   5.0 1.0           1800               46.081002     252.6624     700.3901
         fcfs   5.0 1.0           1800               46.078283     396.3504    1098.3930
          lpm   5.0 1.0           1800               46.078436     295.0969    1264.2117
```

## Best Throughput Row Per Plot Label
```text
   plot_label        policy  rate   k  request_count  throughput_tok_per_sec  ttft_p99_ms
adaptive_dlpm adaptive_dlpm   5.0 1.0           1800               46.151409     661.8047
   dlpm_q1200    dlpm_q1200   5.0 1.0           1800               46.097400     682.8196
   dlpm_q4000    dlpm_q4000   5.0 1.0           1800               46.084566     713.3465
   dlpm_q8000    dlpm_q8000   5.0 1.0           1800               46.081002     700.3901
         fcfs          fcfs   5.0 1.0           1800               46.078283    1098.3930
          lpm           lpm   5.0 1.0           1800               46.078436    1264.2117
```

## Best (Lowest) TTFT P99 Row Per Plot Label
```text
   plot_label        policy  rate   k  request_count  throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
adaptive_dlpm adaptive_dlpm   5.0 1.0           1800               46.151409     203.8188     661.8047
   dlpm_q1200    dlpm_q1200   5.0 1.0           1800               46.097400     237.2203     682.8196
   dlpm_q4000    dlpm_q4000   5.0 1.0           1800               46.084566     246.4739     713.3465
   dlpm_q8000    dlpm_q8000   5.0 1.0           1800               46.081002     252.6624     700.3901
         fcfs          fcfs   5.0 1.0           1800               46.078283     396.3504    1098.3930
          lpm           lpm   5.0 1.0           1800               46.078436     295.0969    1264.2117
```

## High-Load (Max Rate) Median by Policy
```text
               throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
policy                                                         
adaptive_dlpm                  46.151      203.819      661.805
dlpm_q1200                     46.097      237.220      682.820
dlpm_q4000                     46.085      246.474      713.347
dlpm_q8000                     46.081      252.662      700.390
fcfs                           46.078      396.350     1098.393
lpm                            46.078      295.097     1264.212
```

## Median Metrics by Plot Label
```text
               throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
plot_label                                                     
adaptive_dlpm                  46.151      203.819      661.805
dlpm_q1200                     46.097      237.220      682.820
dlpm_q8000                     46.081      252.662      700.390
dlpm_q4000                     46.085      246.474      713.347
fcfs                           46.078      396.350     1098.393
lpm                            46.078      295.097     1264.212
```

## Overall / Dominant / Cold Breakdown

### Overall
```text
   plot_label  throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms  count
adaptive_dlpm               46.151409     203.8188     661.8047   1800
          lpm               46.078436     295.0969    1264.2117   1800
         fcfs               46.078283     396.3504    1098.3930   1799
   dlpm_q1200               46.097400     237.2203     682.8196   1800
   dlpm_q4000               46.084566     246.4739     713.3465   1800
   dlpm_q8000               46.081002     252.6624     700.3901   1800
```

### Dominant
```text
   plot_label  throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms  count
adaptive_dlpm               33.510301     188.5422     553.9897   1530
          lpm               33.426482     266.9229    1096.3342   1530
         fcfs               33.426372     365.6346    1080.3625   1529
   dlpm_q1200               33.442734     221.1452     604.9008   1530
   dlpm_q4000               33.429710     225.4174     639.8899   1530
   dlpm_q8000               33.437204     234.3876     634.8311   1530
```

### Cold
```text
   plot_label  throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms  count
adaptive_dlpm               12.641108     397.3298    1010.2860    270
          lpm               12.651953     463.1085    1805.5198    270
         fcfs               12.651911     590.4867    1143.9641    270
   dlpm_q1200               12.654666     429.8020     915.9742    270
   dlpm_q4000               12.654857     432.7393    1103.0225    270
   dlpm_q8000               12.643798     437.0973     961.3917    270
```

### Quick Read
```text
best_overall_by_ttft_p99: adaptive_dlpm (ttft_p99=661.805 ms)
best_dominant_by_ttft_p99: adaptive_dlpm (ttft_p99=553.990 ms)
worst_cold_by_ttft_p99: lpm (ttft_p99=1805.520 ms)
```

## Request-Level Telemetry Coverage
```text
total_request_rows: 10800
rows_with_Q_at_scheduling: 10799
rows_with_jain_control: 10799
rows_with_aimd_violated=true: 0
```

## Adaptive DLPM Median Q_at_scheduling
```text
adaptive_dlpm: 13500.00
```

## Adaptive AIMD Trace Coverage
```text
adaptive_runs_found: 1
one trace PNG is generated for each adaptive run
```
