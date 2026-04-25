# Benchmark Summary: modal_grid_20260425_010727

Rows: 6
Policies: adaptive_dlpm, dlpm, fcfs, lpm

## Policy Medians
```text
               throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
policy                                                         
adaptive_dlpm                  33.618     1291.303     4740.193
dlpm                           33.462     1220.086     4660.833
fcfs                           31.234     1818.037     4398.107
lpm                            34.324     1212.161     4524.360
```

## Policy Means
```text
               throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
policy                                                         
adaptive_dlpm                  33.618     1291.303     4740.193
dlpm                           33.158     1310.402     4808.050
fcfs                           31.234     1818.037     4398.107
lpm                            34.324     1212.161     4524.360
```

## Best Throughput Row Per Policy
```text
       policy  rate   k  request_count  throughput_tok_per_sec  ttft_p99_ms
adaptive_dlpm   4.0 1.0           1500               33.618428    4740.1931
         dlpm   4.0 1.0           1500               34.157968    4588.3330
         fcfs   4.0 1.0           1500               31.234123    4398.1065
          lpm   4.0 1.0           1500               34.323605    4524.3601
```

## Best (Lowest) TTFT P99 Row Per Policy
```text
       policy  rate   k  request_count  throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
adaptive_dlpm   4.0 1.0           1500               33.618428    1291.3030    4740.1931
         dlpm   4.0 1.0           1500               34.157968    1220.0856    4588.3330
         fcfs   4.0 1.0           1500               31.234123    1818.0368    4398.1065
          lpm   4.0 1.0           1500               34.323605    1212.1610    4524.3601
```

## Best Throughput Row Per Plot Label
```text
   plot_label        policy  rate   k  request_count  throughput_tok_per_sec  ttft_p99_ms
adaptive_dlpm adaptive_dlpm   4.0 1.0           1500               33.618428    4740.1931
   dlpm_q1000          dlpm   4.0 1.0           1500               34.157968    4588.3330
  dlpm_q16000          dlpm   4.0 1.0           1500               31.855234    5174.9854
   dlpm_q4000          dlpm   4.0 1.0           1500               33.462030    4660.8331
         fcfs          fcfs   4.0 1.0           1500               31.234123    4398.1065
          lpm           lpm   4.0 1.0           1500               34.323605    4524.3601
```

## Best (Lowest) TTFT P99 Row Per Plot Label
```text
   plot_label        policy  rate   k  request_count  throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
adaptive_dlpm adaptive_dlpm   4.0 1.0           1500               33.618428    1291.3030    4740.1931
   dlpm_q1000          dlpm   4.0 1.0           1500               34.157968    1220.0856    4588.3330
  dlpm_q16000          dlpm   4.0 1.0           1500               31.855234    1518.6649    5174.9854
   dlpm_q4000          dlpm   4.0 1.0           1500               33.462030    1192.4540    4660.8331
         fcfs          fcfs   4.0 1.0           1500               31.234123    1818.0368    4398.1065
          lpm           lpm   4.0 1.0           1500               34.323605    1212.1610    4524.3601
```

## High-Load (Max Rate) Median by Policy
```text
               throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
policy                                                         
adaptive_dlpm                  33.618     1291.303     4740.193
dlpm                           33.462     1220.086     4660.833
fcfs                           31.234     1818.037     4398.107
lpm                            34.324     1212.161     4524.360
```

## Median Metrics by Plot Label
```text
               throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
plot_label                                                     
fcfs                           31.234     1818.037     4398.107
lpm                            34.324     1212.161     4524.360
dlpm_q1000                     34.158     1220.086     4588.333
dlpm_q4000                     33.462     1192.454     4660.833
adaptive_dlpm                  33.618     1291.303     4740.193
dlpm_q16000                    31.855     1518.665     5174.985
```

## Overall / Dominant / Cold Breakdown

### Overall
```text
   plot_label  throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms  count
adaptive_dlpm               33.618428    1291.3030    4740.1931   1500
          lpm               34.323605    1212.1610    4524.3601   1500
         fcfs               31.234123    1818.0368    4398.1065   1500
   dlpm_q1000               34.157968    1220.0856    4588.3330   1500
   dlpm_q4000               33.462030    1192.4540    4660.8331   1500
  dlpm_q16000               31.855234    1518.6649    5174.9854   1500
```

### Dominant
```text
   plot_label  throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms  count
adaptive_dlpm               10.542625    1043.0165    2444.2453    750
          lpm               10.759444     992.4179    1679.4945    750
         fcfs                9.791393    1487.7455    3907.3664    750
   dlpm_q1000               10.711718     987.6148    1656.6843    750
   dlpm_q4000               10.492728     974.8872    3095.5755    750
  dlpm_q16000                9.985584    1347.8695    2479.1159    750
```

### Cold
```text
   plot_label  throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms  count
adaptive_dlpm               23.075803    2093.6661    5310.3105    750
          lpm               23.564160    1838.6115    4896.6389    750
         fcfs               21.442730    2186.4286    4731.6465    750
   dlpm_q1000               23.446250    2127.4728    4762.0986    750
   dlpm_q4000               22.969302    2132.3291    5002.4254    750
  dlpm_q16000               21.869650    2284.2366    5440.7098    750
```

### Quick Read
```text
best_overall_by_ttft_p99: fcfs (ttft_p99=4398.107 ms)
best_dominant_by_ttft_p99: dlpm_q1000 (ttft_p99=1656.684 ms)
worst_cold_by_ttft_p99: dlpm_q16000 (ttft_p99=5440.710 ms)
```

## Request-Level Telemetry Coverage
```text
total_request_rows: 9000
rows_with_Q_at_scheduling: 9000
rows_with_jain_control: 9000
rows_with_aimd_violated=true: 730
```

## Adaptive DLPM Median Q_at_scheduling
```text
adaptive_dlpm: 2500.00
```

## Adaptive AIMD Trace Coverage
```text
adaptive_runs_found: 1
one trace PNG is generated for each adaptive run
```
