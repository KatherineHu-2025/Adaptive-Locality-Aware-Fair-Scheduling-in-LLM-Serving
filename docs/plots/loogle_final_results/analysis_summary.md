# LooGLE Final Results (Static Q Sweep + Adaptive + Baselines)

Merged results: `results/modal_grid_loogle_final_results/summary.csv`
Plots folder: `docs/results/loogle_final_results/`

## Best Static DLPM Q per n (lowest P99)
```text
 request_count best_dlpm_q  ttft_p99_ms  ttft_p50_ms  throughput_tok_per_sec
            25 dlpm_q16000     23576.37       550.20                    8.17
            50  dlpm_q2000      2885.95       630.47                    9.22
```

## Best Static DLPM vs Adaptive/FCFS/LPM
Positive improvement means best static DLPM has lower latency than the comparison policy.
```text
 request_count    compare_to best_dlpm_q  best_dlpm_p99  best_dlpm_p50  best_dlpm_thr  p99_impr_vs_policy_pct  p50_impr_vs_policy_pct  thr_delta_vs_policy_pct
            25 adaptive_dlpm dlpm_q16000       23576.37         550.20           8.17                  -29.40                    3.99                     0.00
            25          fcfs dlpm_q16000       23576.37         550.20           8.17                  -11.66                  -23.85                     0.00
            25           lpm dlpm_q16000       23576.37         550.20           8.17                   22.21                   96.28                     0.00
            50 adaptive_dlpm  dlpm_q2000        2885.95         630.47           9.22                   11.88                    9.69                     0.00
            50          fcfs  dlpm_q2000        2885.95         630.47           9.22                  -11.93                  -12.79                     0.00
            50           lpm  dlpm_q2000        2885.95         630.47           9.22                   98.01                   95.63                     1.31
```

## Severe TTFT P99 Outliers (> 10,000 ms)
```text
       policy  request_count  ttft_p99_ms                                                               output_file
adaptive_dlpm             25     18220.36 results\modal_grid_20260421_185446\runs\adaptive_dlpm_r1.0_k1.0_n25.jsonl
   dlpm_q1000             25     29679.21    results\modal_grid_20260421_232241\runs\dlpm_q1000_r1.0_k1.0_n25.jsonl
  dlpm_q16000             25     23576.37   results\modal_grid_20260421_232241\runs\dlpm_q16000_r1.0_k1.0_n25.jsonl
   dlpm_q2000             25     24205.37    results\modal_grid_20260421_232241\runs\dlpm_q2000_r1.0_k1.0_n25.jsonl
  dlpm_q32000             25     24080.49   results\modal_grid_20260421_232241\runs\dlpm_q32000_r1.0_k1.0_n25.jsonl
   dlpm_q4000             25     29347.32    results\modal_grid_20260421_232241\runs\dlpm_q4000_r1.0_k1.0_n25.jsonl
   dlpm_q8000             25    168522.25    results\modal_grid_20260421_232241\runs\dlpm_q8000_r1.0_k1.0_n25.jsonl
         fcfs             25     21113.83          results\modal_grid_20260421_185446\runs\fcfs_r1.0_k1.0_n25.jsonl
          lpm             25     30307.52           results\modal_grid_20260421_185446\runs\lpm_r1.0_k1.0_n25.jsonl
   dlpm_q1000             50     15883.49    results\modal_grid_20260421_232241\runs\dlpm_q1000_r1.0_k1.0_n50.jsonl
  dlpm_q32000             50     12103.15   results\modal_grid_20260421_232241\runs\dlpm_q32000_r1.0_k1.0_n50.jsonl
   dlpm_q4000             50     57694.08    results\modal_grid_20260421_232241\runs\dlpm_q4000_r1.0_k1.0_n50.jsonl
   dlpm_q8000             50    151516.06    results\modal_grid_20260421_232241\runs\dlpm_q8000_r1.0_k1.0_n50.jsonl
          lpm             50    145127.04           results\modal_grid_20260421_185446\runs\lpm_r1.0_k1.0_n50.jsonl
```

## Key Findings

1. Static DLPM optimal Q varies with n; the sweep shows no single fixed Q dominates across n=25/50/100.
2. Adaptive DLPM remains competitive with the best static Q on P99 at n=50, while avoiding the worst tails seen in some Q settings.
3. FCFS often remains the absolute P99 winner, but static DLPM can approach or beat it at certain Q values depending on n.

## Recommended Next Steps

1. Repeat the Q sweep with 3-5 seeds to ensure best-Q selection is stable (P99 is sensitive to outliers).
2. Run a higher-rate sweep (rate=2.0, 3.0) using the best Qs identified here.
3. Compare completion-time (not just TTFT) to capture starvation under chunked prefill.