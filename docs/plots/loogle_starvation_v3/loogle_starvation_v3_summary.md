# Benchmark Summary: modal_grid_20260425_220710

Rows: 6
Policies: adaptive_dlpm, dlpm, fcfs, lpm

## Policy Medians
```text
               throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
policy                                                         
adaptive_dlpm                  29.356     2216.728     5636.311
dlpm                           28.837     2005.763     5656.877
fcfs                           26.714     2329.030     6088.889
lpm                            28.883     1578.041     5517.304
```

## Policy Means
```text
               throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
policy                                                         
adaptive_dlpm                  29.356     2216.728     5636.311
dlpm                           28.686     2022.636     5656.218
fcfs                           26.714     2329.030     6088.889
lpm                            28.883     1578.041     5517.304
```

## Best Throughput Row Per Policy
```text
       policy  rate   k  request_count  throughput_tok_per_sec  ttft_p99_ms
adaptive_dlpm   4.0 1.0           1200               29.356423    5636.3110
         dlpm   4.0 1.0           1200               28.999171    5774.0313
         fcfs   4.0 1.0           1200               26.713574    6088.8890
          lpm   4.0 1.0           1200               28.882535    5517.3044
```

## Best (Lowest) TTFT P99 Row Per Policy
```text
       policy  rate   k  request_count  throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
adaptive_dlpm   4.0 1.0           1200               29.356423    2216.7282    5636.3110
         dlpm   4.0 1.0           1200               28.223401    2069.3658    5537.7466
         fcfs   4.0 1.0           1200               26.713574    2329.0302    6088.8890
          lpm   4.0 1.0           1200               28.882535    1578.0408    5517.3044
```

## Best Throughput Row Per Plot Label
```text
   plot_label        policy  rate   k  request_count  throughput_tok_per_sec  ttft_p99_ms
adaptive_dlpm adaptive_dlpm   4.0 1.0           1200               29.356423    5636.3110
   dlpm_q1200          dlpm   4.0 1.0           1200               28.836598    5656.8770
   dlpm_q4000          dlpm   4.0 1.0           1200               28.999171    5774.0313
   dlpm_q8000          dlpm   4.0 1.0           1200               28.223401    5537.7466
         fcfs          fcfs   4.0 1.0           1200               26.713574    6088.8890
          lpm           lpm   4.0 1.0           1200               28.882535    5517.3044
```

## Best (Lowest) TTFT P99 Row Per Plot Label
```text
   plot_label        policy  rate   k  request_count  throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
adaptive_dlpm adaptive_dlpm   4.0 1.0           1200               29.356423    2216.7282    5636.3110
   dlpm_q1200          dlpm   4.0 1.0           1200               28.836598    2005.7626    5656.8770
   dlpm_q4000          dlpm   4.0 1.0           1200               28.999171    1992.7801    5774.0313
   dlpm_q8000          dlpm   4.0 1.0           1200               28.223401    2069.3658    5537.7466
         fcfs          fcfs   4.0 1.0           1200               26.713574    2329.0302    6088.8890
          lpm           lpm   4.0 1.0           1200               28.882535    1578.0408    5517.3044
```

## High-Load (Max Rate) Median by Policy
```text
               throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
policy                                                         
adaptive_dlpm                  29.356     2216.728     5636.311
dlpm                           28.837     2005.763     5656.877
fcfs                           26.714     2329.030     6088.889
lpm                            28.883     1578.041     5517.304
```

## Median Metrics by Plot Label
```text
               throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
plot_label                                                     
lpm                            28.883     1578.041     5517.304
dlpm_q8000                     28.223     2069.366     5537.747
adaptive_dlpm                  29.356     2216.728     5636.311
dlpm_q1200                     28.837     2005.763     5656.877
dlpm_q4000                     28.999     1992.780     5774.031
fcfs                           26.714     2329.030     6088.889
```

## Overall / Dominant / Cold Breakdown

### Overall
```text
   plot_label  throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms  count
adaptive_dlpm               29.356423    2216.7282    5636.3110   1200
          lpm               28.882535    1578.0408    5517.3044   1199
         fcfs               26.713574    2329.0302    6088.8890   1183
   dlpm_q1200               28.836598    2005.7626    5656.8770   1200
   dlpm_q4000               28.999171    1992.7801    5774.0313   1200
   dlpm_q8000               28.223401    2069.3658    5537.7466   1200
```

### Dominant
```text
   plot_label  throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms  count
adaptive_dlpm                4.812637    1136.6938    4903.9777    360
          lpm                4.740375    1144.7376    3296.3909    360
         fcfs                4.327770    2110.4413    5614.4077    352
   dlpm_q1200                4.730966     959.1739    4359.0937    360
   dlpm_q4000                4.757344     984.0095    5127.0355    360
   dlpm_q8000                4.628224    1199.1446    4805.5575    360
```

### Cold
```text
   plot_label  throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms  count
adaptive_dlpm               24.543786    2666.8847    5982.0321    840
          lpm               24.142160    2120.2214    6008.0613    839
         fcfs               22.385804    2438.0116    6088.8890    831
   dlpm_q1200               24.105632    2645.7522    5746.4244    840
   dlpm_q4000               24.241827    2730.7528    5933.9256    840
   dlpm_q8000               23.595177    2748.0141    5631.0449    840
```

### Quick Read
```text
best_overall_by_ttft_p99: lpm (ttft_p99=5517.304 ms)
best_dominant_by_ttft_p99: lpm (ttft_p99=3296.391 ms)
worst_cold_by_ttft_p99: fcfs (ttft_p99=6088.889 ms)
```

## Request-Level Telemetry Coverage
```text
total_request_rows: 7200
rows_with_Q_at_scheduling: 7182
rows_with_jain_control: 7182
rows_with_aimd_violated=true: 1186
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
