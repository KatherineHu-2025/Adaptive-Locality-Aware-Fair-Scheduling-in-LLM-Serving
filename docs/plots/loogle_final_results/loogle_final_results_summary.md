# Benchmark Summary: modal_grid_loogle_final_results

Rows: 21
Policies: adaptive_dlpm, dlpm_q1000, dlpm_q16000, dlpm_q2000, dlpm_q32000, dlpm_q4000, dlpm_q8000, fcfs, lpm

## Policy Medians
```text
               throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
policy                                                         
adaptive_dlpm                   8.520      698.128     6602.793
dlpm_q1000                      8.692     8519.681    22781.347
dlpm_q16000                     8.692      597.799    13232.436
dlpm_q2000                      8.692      570.683    13545.659
dlpm_q32000                     8.692     1582.203    18091.817
dlpm_q4000                      8.692      759.979    43520.697
dlpm_q8000                      8.692     6623.153   160019.151
fcfs                            8.524      558.975     4164.902
lpm                             8.524    14440.707    30307.517
```

## Policy Means
```text
               throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
policy                                                         
adaptive_dlpm                   8.635      878.618     9366.031
dlpm_q1000                      8.692     8519.681    22781.347
dlpm_q16000                     8.692      597.799    13232.436
dlpm_q2000                      8.692      570.683    13545.659
dlpm_q32000                     8.692     1582.203    18091.817
dlpm_q4000                      8.692      759.979    43520.697
dlpm_q8000                      8.692     6623.153   160019.151
fcfs                            8.636      696.172     9285.712
lpm                             8.597    10200.163    60488.877
```

## Best Throughput Row Per Policy
```text
       policy  rate   k  request_count  throughput_tok_per_sec  ttft_p99_ms
adaptive_dlpm   1.0 1.0             50                9.216925    3274.9426
   dlpm_q1000   1.0 1.0             50                9.216960   15883.4885
  dlpm_q16000   1.0 1.0             50                9.216878    2888.5036
   dlpm_q2000   1.0 1.0             50                9.216961    2885.9510
  dlpm_q32000   1.0 1.0             50                9.216985   12103.1483
   dlpm_q4000   1.0 1.0             50                9.216878   57694.0769
   dlpm_q8000   1.0 1.0             50                9.216991  151516.0571
         fcfs   1.0 1.0             50                9.216926    2578.4043
          lpm   1.0 1.0             50                9.097646  145127.0359
```

## Best (Lowest) TTFT P99 Row Per Policy
```text
       policy  rate   k  request_count  throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
adaptive_dlpm   1.0 1.0             50                9.216925     698.1283    3274.9426
   dlpm_q1000   1.0 1.0             50                9.216960    3964.1245   15883.4885
  dlpm_q16000   1.0 1.0             50                9.216878     645.3963    2888.5036
   dlpm_q2000   1.0 1.0             50                9.216961     630.4692    2885.9510
  dlpm_q32000   1.0 1.0             50                9.216985    1301.1844   12103.1483
   dlpm_q4000   1.0 1.0             25                8.167826     578.5135   29347.3170
   dlpm_q8000   1.0 1.0             50                9.216991    1534.7045  151516.0571
         fcfs   1.0 1.0             50                9.216926     558.9755    2578.4043
          lpm   1.0 1.0            100                8.524475    1355.7207    6032.0794
```

## High-Load (Max Rate) Median by Policy
```text
               throughput_tok_per_sec  ttft_p50_ms  ttft_p99_ms
policy                                                         
adaptive_dlpm                   8.520      698.128     6602.793
dlpm_q1000                      8.692     8519.681    22781.347
dlpm_q16000                     8.692      597.799    13232.436
dlpm_q2000                      8.692      570.683    13545.659
dlpm_q32000                     8.692     1582.203    18091.817
dlpm_q4000                      8.692      759.979    43520.697
dlpm_q8000                      8.692     6623.153   160019.151
fcfs                            8.524      558.975     4164.902
lpm                             8.524    14440.707    30307.517
```

## Severe TTFT P99 Outliers (> 10,000 ms)
```text
       policy  rate   k  request_count  ttft_p99_ms                                                               output_file
adaptive_dlpm   1.0 1.0             25   18220.3575 results\modal_grid_20260421_185446\runs\adaptive_dlpm_r1.0_k1.0_n25.jsonl
   dlpm_q1000   1.0 1.0             25   29679.2053    results\modal_grid_20260421_232241\runs\dlpm_q1000_r1.0_k1.0_n25.jsonl
  dlpm_q16000   1.0 1.0             25   23576.3676   results\modal_grid_20260421_232241\runs\dlpm_q16000_r1.0_k1.0_n25.jsonl
   dlpm_q2000   1.0 1.0             25   24205.3670    results\modal_grid_20260421_232241\runs\dlpm_q2000_r1.0_k1.0_n25.jsonl
  dlpm_q32000   1.0 1.0             25   24080.4850   results\modal_grid_20260421_232241\runs\dlpm_q32000_r1.0_k1.0_n25.jsonl
   dlpm_q4000   1.0 1.0             25   29347.3170    results\modal_grid_20260421_232241\runs\dlpm_q4000_r1.0_k1.0_n25.jsonl
   dlpm_q8000   1.0 1.0             25  168522.2451    results\modal_grid_20260421_232241\runs\dlpm_q8000_r1.0_k1.0_n25.jsonl
         fcfs   1.0 1.0             25   21113.8315          results\modal_grid_20260421_185446\runs\fcfs_r1.0_k1.0_n25.jsonl
          lpm   1.0 1.0             25   30307.5170           results\modal_grid_20260421_185446\runs\lpm_r1.0_k1.0_n25.jsonl
   dlpm_q1000   1.0 1.0             50   15883.4885    results\modal_grid_20260421_232241\runs\dlpm_q1000_r1.0_k1.0_n50.jsonl
  dlpm_q32000   1.0 1.0             50   12103.1483   results\modal_grid_20260421_232241\runs\dlpm_q32000_r1.0_k1.0_n50.jsonl
   dlpm_q4000   1.0 1.0             50   57694.0769    results\modal_grid_20260421_232241\runs\dlpm_q4000_r1.0_k1.0_n50.jsonl
   dlpm_q8000   1.0 1.0             50  151516.0571    results\modal_grid_20260421_232241\runs\dlpm_q8000_r1.0_k1.0_n50.jsonl
          lpm   1.0 1.0             50  145127.0359           results\modal_grid_20260421_185446\runs\lpm_r1.0_k1.0_n50.jsonl
```

## Request-Level Telemetry Coverage
```text
total_request_rows: 7509
rows_with_Q_at_scheduling: 7508
rows_with_jain_control: 7508
rows_with_aimd_violated=true: 709
```

## Adaptive DLPM Median Q_at_scheduling
```text
adaptive_dlpm: 1700.00
```

## Adaptive AIMD Trace Coverage
```text
adaptive_runs_found: 3
one trace PNG is generated for each adaptive run
```
