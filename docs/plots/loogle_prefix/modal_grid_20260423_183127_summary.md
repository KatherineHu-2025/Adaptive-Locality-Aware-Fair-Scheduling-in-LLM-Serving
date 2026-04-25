# Benchmark Summary: modal_grid_20260423_183127

Rows: 9
Policies: adaptive_dlpm, dlpm, fcfs, lpm

## Policy Medians
```text
               throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
policy                                                         
adaptive_dlpm                  26.847     1108.292    17012.595
dlpm                           26.851     1059.360    17513.506
fcfs                           26.857     1344.627    24305.117
lpm                            26.810     1183.804    19337.127
```

## Policy Means
```text
               throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
policy                                                         
adaptive_dlpm                  26.847     1108.292    17012.595
dlpm                           26.850     1090.014    18527.948
fcfs                           26.857     1344.627    24305.117
lpm                            26.810     1183.804    19337.127
```

## Best Throughput Row Per Policy
```text
       policy  rate   k  request_count  throughput_tok_per_sec  ttft_p99_ms
adaptive_dlpm   2.0 1.0            400               26.846574   17012.5949
         dlpm   2.0 1.0            400               26.856487   18088.6820
         fcfs   2.0 1.0            400               26.856914   24305.1168
          lpm   2.0 1.0            400               26.810224   19337.1266
```

## Best (Lowest) TTFT P99 Row Per Policy
```text
       policy  rate   k  request_count  throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
adaptive_dlpm   2.0 1.0            400               26.846574    1108.2924   17012.5949
         dlpm   2.0 1.0            400               26.855858    1009.2661   16427.5500
         fcfs   2.0 1.0            400               26.856914    1344.6266   24305.1168
          lpm   2.0 1.0            400               26.810224    1183.8041   19337.1266
```

## Best Throughput Row Per Plot Label
```text
   plot_label        policy  rate   k  request_count  throughput_tok_per_sec  ttft_p99_ms
adaptive_dlpm adaptive_dlpm   2.0 1.0            400               26.846574   17012.5949
   dlpm_q1000          dlpm   2.0 1.0            400               26.846449   16938.3296
  dlpm_q16000          dlpm   2.0 1.0            400               26.855858   16427.5500
   dlpm_q2000          dlpm   2.0 1.0            400               26.840396   16873.1532
  dlpm_q32000          dlpm   2.0 1.0            400               26.855993   19698.4561
   dlpm_q4000          dlpm   2.0 1.0            400               26.856487   18088.6820
   dlpm_q8000          dlpm   2.0 1.0            400               26.846793   23141.5193
         fcfs          fcfs   2.0 1.0            400               26.856914   24305.1168
          lpm           lpm   2.0 1.0            400               26.810224   19337.1266
```

## Best (Lowest) TTFT P99 Row Per Plot Label
```text
   plot_label        policy  rate   k  request_count  throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
adaptive_dlpm adaptive_dlpm   2.0 1.0            400               26.846574    1108.2924   17012.5949
   dlpm_q1000          dlpm   2.0 1.0            400               26.846449    1018.6827   16938.3296
  dlpm_q16000          dlpm   2.0 1.0            400               26.855858    1009.2661   16427.5500
   dlpm_q2000          dlpm   2.0 1.0            400               26.840396    1115.0404   16873.1532
  dlpm_q32000          dlpm   2.0 1.0            400               26.855993    1325.0851   19698.4561
   dlpm_q4000          dlpm   2.0 1.0            400               26.856487     971.9700   18088.6820
   dlpm_q8000          dlpm   2.0 1.0            400               26.846793    1100.0380   23141.5193
         fcfs          fcfs   2.0 1.0            400               26.856914    1344.6266   24305.1168
          lpm           lpm   2.0 1.0            400               26.810224    1183.8041   19337.1266
```

## High-Load (Max Rate) Median by Policy
```text
               throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
policy                                                         
adaptive_dlpm                  26.847     1108.292    17012.595
dlpm                           26.851     1059.360    17513.506
fcfs                           26.857     1344.627    24305.117
lpm                            26.810     1183.804    19337.127
```

## Median Metrics by Plot Label
```text
               throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
plot_label                                                     
dlpm_q16000                    26.856     1009.266    16427.550
dlpm_q2000                     26.840     1115.040    16873.153
dlpm_q1000                     26.846     1018.683    16938.330
adaptive_dlpm                  26.847     1108.292    17012.595
dlpm_q4000                     26.856      971.970    18088.682
lpm                            26.810     1183.804    19337.127
dlpm_q32000                    26.856     1325.085    19698.456
dlpm_q8000                     26.847     1100.038    23141.519
fcfs                           26.857     1344.627    24305.117
```

## Overall / Dominant / Cold Breakdown

### Overall
```text
   plot_label  throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms  count
adaptive_dlpm               26.846574    1108.2924   17012.5949    400
          lpm               26.810224    1183.8041   19337.1266    399
         fcfs               26.856914    1344.6266   24305.1168    400
   dlpm_q1000               26.846449    1018.6827   16938.3296    400
   dlpm_q2000               26.840396    1115.0404   16873.1532    400
   dlpm_q4000               26.856487     971.9700   18088.6820    400
   dlpm_q8000               26.846793    1100.0380   23141.5193    400
  dlpm_q16000               26.855858    1009.2661   16427.5500    400
  dlpm_q32000               26.855993    1325.0851   19698.4561    400
```

### Dominant
```text
   plot_label  throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms  count
adaptive_dlpm                8.176186     802.3730    3075.6343    200
          lpm                8.140531     865.3664   18717.5019    199
         fcfs                8.171208    1060.5963    3241.4777    200
   dlpm_q1000                8.176148     745.1512    2860.0872    200
   dlpm_q2000                8.170792     871.9435    2847.0077    200
   dlpm_q4000                8.176129     747.2221    3702.2408    200
   dlpm_q8000                8.176252     847.7705    2812.7682    200
  dlpm_q16000                8.170887     684.9427    3957.5542    200
  dlpm_q32000                8.175978    1078.9370    3025.8749    200
```

### Cold
```text
   plot_label  throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms  count
adaptive_dlpm               18.670388    1390.4665   17012.5949    200
          lpm               18.669692    1503.5972   19466.5327    200
         fcfs               18.685705    1618.2490   24896.9662    200
   dlpm_q1000               18.670301    1388.3713   16938.3296    200
   dlpm_q2000               18.669604    1427.8466   16873.1532    200
   dlpm_q4000               18.680358    1407.2968   18088.6820    200
   dlpm_q8000               18.670540    1494.1081   23141.5193    200
  dlpm_q16000               18.684971    1319.6243   16427.5500    200
  dlpm_q32000               18.680015    1685.9074   19698.4561    200
```

### Quick Read
```text
best_overall_by_ttft_p99: dlpm_q16000 (ttft_p99=16427.550 ms)
best_dominant_by_ttft_p99: dlpm_q8000 (ttft_p99=2812.768 ms)
worst_cold_by_ttft_p99: fcfs (ttft_p99=24896.966 ms)
```

## Severe TTFT P99 Outliers (> 10,000 ms)
```text
   plot_label        policy  rate   k  request_count  ttft_p99_ms                                                                output_file
adaptive_dlpm adaptive_dlpm   2.0 1.0            400   17012.5949 results\modal_grid_20260423_183127\runs\adaptive_dlpm_r2.0_k1.0_n400.jsonl
          lpm           lpm   2.0 1.0            400   19337.1266           results\modal_grid_20260423_183127\runs\lpm_r2.0_k1.0_n400.jsonl
         fcfs          fcfs   2.0 1.0            400   24305.1168          results\modal_grid_20260423_183127\runs\fcfs_r2.0_k1.0_n400.jsonl
   dlpm_q1000          dlpm   2.0 1.0            400   16938.3296    results\modal_grid_20260423_183127\runs\dlpm_q1000_r2.0_k1.0_n400.jsonl
   dlpm_q2000          dlpm   2.0 1.0            400   16873.1532    results\modal_grid_20260423_183127\runs\dlpm_q2000_r2.0_k1.0_n400.jsonl
   dlpm_q4000          dlpm   2.0 1.0            400   18088.6820    results\modal_grid_20260423_183127\runs\dlpm_q4000_r2.0_k1.0_n400.jsonl
   dlpm_q8000          dlpm   2.0 1.0            400   23141.5193    results\modal_grid_20260423_183127\runs\dlpm_q8000_r2.0_k1.0_n400.jsonl
  dlpm_q16000          dlpm   2.0 1.0            400   16427.5500   results\modal_grid_20260423_183127\runs\dlpm_q16000_r2.0_k1.0_n400.jsonl
  dlpm_q32000          dlpm   2.0 1.0            400   19698.4561   results\modal_grid_20260423_183127\runs\dlpm_q32000_r2.0_k1.0_n400.jsonl
```

## Request-Level Telemetry Coverage
```text
total_request_rows: 3600
rows_with_Q_at_scheduling: 3599
rows_with_jain_control: 3599
rows_with_aimd_violated=true: 383
```

## Adaptive DLPM Median Q_at_scheduling
```text
adaptive_dlpm: 1200.00
```

## Adaptive AIMD Trace Coverage
```text
adaptive_runs_found: 1
one trace PNG is generated for each adaptive run
```
